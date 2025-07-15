import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

def rate_limited_get(url, headers=None, params=None, max_retries=3):
    """Wrapper for requests.get that automatically handles rate limiting"""
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers, params=params)
        
        # Check if we hit a rate limit
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            # Get the reset time from headers if available
            reset_time = response.headers.get('X-RateLimit-Reset')
            if reset_time:
                # Wait until reset time + a small buffer
                wait_time = int(reset_time) - int(time.time()) + 10
                print(f"    Rate limit hit. Waiting {wait_time} seconds until reset...")
                time.sleep(max(wait_time, 30))  # Wait at least 30 seconds
            else:
                # No reset time available, use shorter backoff
                wait_time = (2 ** attempt) * 30  # 30s, 60s, 120s
                print(f"    Rate limit hit (attempt {attempt + 1}). Waiting {wait_time} seconds...")
                time.sleep(wait_time)
        elif response.status_code == 202:
            # Search is being indexed, wait a bit
            print(f"    Search indexing in progress, waiting 30 seconds...")
            time.sleep(30)
        elif response.status_code == 422:
            # Validation error - log the details
            print(f"    Validation error for query: {params.get('q', 'unknown')}")
            print(f"    Response: {response.text}")
            return response
        else:
            # Success or other error, return the response
            return response
    
    # If we've exhausted retries, return the last response
    print(f"    Max retries exceeded for {url}")
    return response

def get_coauthored_commits(username, token, date_range=None, email=None):
    url = f"https://api.github.com/search/commits"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Build query with username and/or email
    query_parts = []
    if username:
        query_parts.append(f'co-authored-by:{username}')
    if email:
        query_parts.append(f'co-authored-by:{email}')
    
    query = ' OR '.join(query_parts) if query_parts else 'co-authored-by:nonexistent'
    
    if date_range:
        query += f' committer-date:{date_range}'
    
    params = {
        'q': query,
        'per_page': 1
    }
    
    response = rate_limited_get(url, headers=headers, params=params)
    return response.json()

def get_commits_by_author(username, token, date_range=None, email=None):
    """Get commits where username/email is the primary author"""
    url = f"https://api.github.com/search/commits"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Build query with username and/or email
    query_parts = []
    if username:
        query_parts.append(f'author:{username}')
    if email:
        query_parts.append(f'author-email:{email}')
    
    query = ' OR '.join(query_parts) if query_parts else 'author:nonexistent'
    
    if date_range:
        query += f' committer-date:{date_range}'
    
    params = {
        'q': query,
        'per_page': 1
    }
    
    response = rate_limited_get(url, headers=headers, params=params)
    return response.json()

def get_activity(username, token, search_type, date_range=None, email=None):
    """Get activity from GitHub for any username/email
    search_type: 'issues', 'repositories', 'code'
    """
    url = f"https://api.github.com/search/{search_type}"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Different search queries for different types
    if search_type == 'issues':
        # Search for issues and PRs mentioning the user/email
        query_parts = []
        if username:
            query_parts.append(f'is:issue "{username}" OR mentions:{username} OR "co-authored-by {username}"')
        if email:
            query_parts.append(f'is:issue "{email}" OR "co-authored-by {email}"')
        query = ' OR '.join(query_parts) if query_parts else 'is:issue nonexistent'
    elif search_type == 'repositories':
        # Repositories with username/email in name/description
        query_parts = []
        if username:
            query_parts.append(f'{username} in:name,description,readme')
        if email:
            query_parts.append(f'{email} in:name,description,readme')
        query = ' OR '.join(query_parts) if query_parts else 'nonexistent in:name'
    elif search_type == 'code':
        # Code files mentioning username/email
        query_parts = []
        if username:
            query_parts.append(f'"co-authored-by {username}" OR "{username} code" OR "generated with {username}"')
        if email:
            query_parts.append(f'"co-authored-by {email}" OR "{email} code"')
        query = ' OR '.join(query_parts) if query_parts else '"nonexistent"'
    else:
        return {'error': f'Unsupported search type: {search_type}'}
    
    if date_range and search_type in ['issues']:
        query += f' created:{date_range}'
    
    params = {
        'q': query,
        'per_page': 1
    }
    
    response = rate_limited_get(url, headers=headers, params=params)
    return response.json()

def collect_user_stats(display_name, username, token, email=None):
    """Collect all stats for a user and return as dict"""
    print(f"Collecting data for {display_name}...")
    
    stats = {
        "display_name": display_name,
        "username": username,
        "email": email,
        "overall_stats": {},
        "weekly_growth": []
    }
    
    # Overall stats
    activities = [
        ("commits_coauthored", lambda: get_coauthored_commits(username, token, email=email)),
        ("commits_primary_author", lambda: get_commits_by_author(username, token, email=email)),
        # ("issues_mentioning", lambda: get_activity(username, token, 'issues', email=email)),  # Disabled - API query issues
        ("repositories_mentioning", lambda: get_activity(username, token, 'repositories', email=email)),
        # ("code_files_mentioning", lambda: get_activity(username, token, 'code', email=email)),  # Disabled - searches code content
    ]
    
    for stat_name, get_data in activities:
        result = get_data()
        if 'total_count' in result:
            stats["overall_stats"][stat_name] = result['total_count']
            print(f"  {stat_name}: {result['total_count']:,}")
        else:
            stats["overall_stats"][stat_name] = None
            error_msg = result.get('message', 'Unknown error')
            print(f"  {stat_name}: Error - {error_msg}")
            if 'errors' in result:
                print(f"    Details: {result['errors']}")
    
    return stats

def collect_weekly_growth(username, token, start_date, email=None):
    """Collect weekly growth data for both co-authored and primary author commits"""
    print(f"  Weekly commits breakdown:")
    weekly_data = []
    current_date = datetime.now()
    week_start = start_date
    
    while week_start < current_date:
        week_end = min(week_start + timedelta(days=6), current_date)
        
        period_name = f"{week_start.strftime('%b %d')}-{week_end.strftime('%d')}"
        date_range = f"{week_start.strftime('%Y-%m-%d')}..{week_end.strftime('%Y-%m-%d')}"
        
        # Get co-authored commits
        coauth_result = get_coauthored_commits(username, token, date_range, email=email)
        coauth_count = coauth_result.get('total_count', 0) if 'total_count' in coauth_result else None
        
        # Get primary author commits  
        primary_result = get_commits_by_author(username, token, date_range, email=email)
        primary_count = primary_result.get('total_count', 0) if 'total_count' in primary_result else None
        
        week_data = {
            "period": period_name,
            "start_date": week_start.strftime('%Y-%m-%d'),
            "end_date": week_end.strftime('%Y-%m-%d'),
            "commits_coauthored": coauth_count,
            "commits_primary_author": primary_count
        }
        
        # Print to terminal
        if coauth_count is not None and primary_count is not None:
            total = coauth_count + primary_count
            print(f"    {period_name}: {coauth_count:,} co-auth + {primary_count:,} primary = {total:,} total")
        else:
            print(f"    {period_name}: Error")
        
        weekly_data.append(week_data)
        week_start += timedelta(days=7)
        
        # Small delay between weekly requests to be gentle on the API
        time.sleep(1)
    
    return weekly_data

if __name__ == "__main__":
    load_dotenv()
    token = os.getenv('GITHUB_TOKEN')

    print("=== AI Assistant Activity Analysis ===")
    
    # Define the users to analyze with their launch dates
    # Format: (display_name, username, launch_date, email)
    # email is optional - set to None if not needed
    users = [
        ("Claude Code", "claude", datetime(2025, 2, 24), None),
        ("Jules", "google-labs-jules[bot]", datetime(2025, 2, 24), None),
        # ("Windsurf", "windsurf-bot[bot]", datetime(2025, 2, 24), None),
        ("Cursor", "cursoragent", datetime(2025, 2, 24), None),
        ("Copilot (coauthored only)", "Copilot", datetime(2025, 2, 24), None)
    ]
    
    all_data = {
        "analysis_date": datetime.now().isoformat(),
        "users": []
    }
    
    # Collect data for each user
    for i, (display_name, username, launch_date, email) in enumerate(users):
        print(f"\n--- Analyzing {display_name} ---")
        
        # Get overall stats
        user_stats = collect_user_stats(display_name, username, token, email=email)
        
        # Get weekly growth data
        print(f"Collecting weekly growth data for {display_name}...")
        user_stats["weekly_growth"] = collect_weekly_growth(username, token, launch_date, email=email)
        
        all_data["users"].append(user_stats)
        
        print(f"Completed analysis for {display_name}")
        
        # Wait 30 seconds between users to avoid rate limits (except for the last user)
        if i < len(users) - 1:
            print(f"Waiting 30 seconds to avoid rate limits...")
            time.sleep(30)
    
    # Write to JSON file
    output_file = "data/ai_assistant_github_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\nAnalysis complete! Data saved to {output_file}")
    
    # Print summary
    print(f"\n=== Summary ===")
    for user_data in all_data["users"]:
        name = user_data["display_name"]
        stats = user_data["overall_stats"]
        coauth = stats.get("commits_coauthored", 0) or 0
        primary = stats.get("commits_primary_author", 0) or 0
        print(f"{name}: {coauth:,} co-authored + {primary:,} primary = {coauth + primary:,} total commits")
