import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.patheffects as path_effects
import matplotlib.font_manager as fm
import numpy as np
from datetime import datetime, timedelta
import requests
from PIL import Image
import io
import seaborn as sns
import os

# Configure xkcd font properly
def setup_xkcd_font():
    """Set up the xkcd font for matplotlib"""
    font_path = 'fonts/xkcd-script.otf'
    if os.path.exists(font_path):
        # Register the font with matplotlib
        fm.fontManager.addfont(font_path)
        # Set the font family for xkcd style
        plt.rcParams['font.family'] = 'xkcd Script'
    else:
        print("xkcd font not found at 'fonts/xkcd-script.otf'")
        print("Please download the xkcd font first or run the setup script.")
        exit(1)

# Set up the plotting style for friendly, hand-drawn charts using xkcd style
setup_xkcd_font()
plt.xkcd()  # Enable xkcd-style drawing
sns.set_palette("husl")

def load_data(json_file="data/ai_assistant_github_analysis.json"):
    """Load the analysis data from JSON file"""
    with open(json_file, 'r') as f:
        return json.load(f)

def download_github_avatar(username, size=64):
    """Download GitHub user avatar"""
    try:
        url = f"https://github.com/{username}.png?size={size}"
        response = requests.get(url)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        else:
            return None
    except:
        return None

def create_smooth_line(x, y, smooth_factor=0.3):
    """Create smooth, natural-looking curved lines for xkcd style"""
    if len(x) < 3:
        return x, y
    
    # Use cubic interpolation for smooth curves
    from scipy.interpolate import interp1d
    
    # Create more points for smoother curves (xkcd style will handle the squiggles)
    x_smooth = np.linspace(min(x), max(x), len(x) * 2)
    
    if len(x) > 2:
        f = interp1d(x, y, kind='cubic', bounds_error=False, fill_value='extrapolate')
        y_smooth = f(x_smooth)
        return x_smooth, y_smooth
    else:
        return x, y

def plot_weekly_commits(data, save_path="plots/weekly_commits_chart.png"):
    """Create a growth chart of weekly commits"""
    
    # AI assistant colors from their icons
    colors = {
        'Claude': '#D97554',      # Claude orange
        'Jules': '#715CD7',       # Jules purple
        'Cursor': '#000000',      # Cursor black  
        'Copilot': '#F6F8FA',     # Copilot light gray (back to original)
        'Windsurf': '#FECA57'     # Warm yellow
    }
    
    # Create figure with clean styling
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    
    # Remove top and right spines for cleaner look
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e0e0e0')
    ax.spines['bottom'].set_color('#e0e0e0')
    
    # Fixed end date for consistent comparison
    min_end_date = datetime(2025, 7, 8)
    print(f"Using fixed end date for comparison: {min_end_date.strftime('%Y-%m-%d')}")
    
    max_commits = 0
    legend_elements = []
    
    for user_data in data['users']:
        name = user_data['display_name']
        weekly_data = user_data['weekly_growth']
        
        if not weekly_data:
            continue
            
        # Prepare data for plotting
        dates = []
        total_commits = []
        running_total = 0
        
        for week in weekly_data:
            # Skip weeks before 2025-02-04
            week_start_date = datetime.strptime(week['start_date'], '%Y-%m-%d')
            if week_start_date < datetime(2025, 2, 24):
                continue
            
            # Skip weeks after the fixed end date
            week_end_date = datetime.strptime(week['end_date'], '%Y-%m-%d')
            if min_end_date and week_end_date > min_end_date:
                print(min_end_date, week_end_date)
                continue
                
            # Handle null values by treating them as 0
            coauthored = week['commits_coauthored'] if week['commits_coauthored'] is not None else 0
            primary = week['commits_primary_author'] if week['commits_primary_author'] is not None else 0
            
            # For Copilot, only count co-authored commits due to data issues with primary author
            if name == 'Copilot':
                week_total = coauthored
            else:
                week_total = coauthored + primary
            
            running_total += week_total
            dates.append(week_start_date)
            total_commits.append(running_total)
        
        if not dates:
            continue
            
        # Convert to numpy arrays for plotting
        dates_array = np.array(dates)
        commits_array = np.array(total_commits)
        
        # Plot the line with raw data (no smoothing)
        color = colors.get(name, '#333333')
        
        # Simple line plotting - xkcd style handles the squiggly appearance
        if name == 'Copilot':
            # Add grayer border for light Copilot color visibility
            ax.plot(dates_array, commits_array, color='#888888', linewidth=5, 
                   alpha=0.9, zorder=8)
            ax.plot(dates_array, commits_array, color=color, linewidth=3.5, 
                   alpha=0.9, label=name, zorder=9)
        else:
            ax.plot(dates_array, commits_array, color=color, linewidth=3.5, 
                   alpha=0.9, label=name, zorder=10)
        
        max_commits = max(max_commits, max(total_commits))
        
        # Download and prepare avatar for legend
        username_map = {
            'Claude': 'icons/claude.png',
            'Jules': 'icons/jules.png', 
            'Cursor': 'icons/cursor.png',
            'Copilot': 'icons/copilot.png',
            # 'Windsurf': 'windsurf-ai'  # Commented out
        }
        
        # Try to load local icon first, fallback to GitHub avatar
        icon_path = username_map.get(name)
        avatar = None
        if icon_path:
            try:
                avatar = Image.open(icon_path)
            except:
                # Fallback to GitHub avatar if local icon not found
                github_usernames = {
                    'Claude': 'claude-ai',
                    'Jules': 'google-labs-jules[bot]', 
                    'Cursor': 'cursor-ai',
                    'Copilot': 'github-copilot',
                }
                avatar = download_github_avatar(github_usernames.get(name, name.lower()))
        
        if avatar:
            # Create legend element with avatar
            legend_elements.append((name, color, avatar))
        else:
            legend_elements.append((name, color, None))
    
    # Styling
    ax.set_title('GitHub activity (coauthored commits)', 
                fontsize=24, fontweight='bold', color='#2c3e50', pad=35)
    ax.set_xlabel('Date', fontsize=20, color='#34495e')
    ax.set_ylabel('Cumulative Commits', fontsize=20, color='#34495e')
    
    # Format y-axis with nice numbers
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1000)}K' if x >= 1000 else str(int(x))))
    
    # Grid styling
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Custom legend with icons replacing color boxes
    legend_y = 0.95
    for i, (name, color, avatar) in enumerate(legend_elements):
        y_pos = legend_y - (i * 0.08)
        
        # Use icon as legend indicator instead of color box
        if avatar:
            # Resize avatar to small size for legend indicator
            avatar_resized = avatar.resize((24, 24), Image.Resampling.LANCZOS)
            
            # Add icon as legend indicator
            imagebox = OffsetImage(avatar_resized, zoom=1.0)
            ab = AnnotationBbox(imagebox, (0.035, y_pos), 
                              xycoords='axes fraction', frameon=True,
                              box_alignment=(0.5, 0.5))
            # Add subtle border and rounded appearance
            ab.patch.set_boxstyle("round,pad=0.002")
            ab.patch.set_edgecolor('#e0e0e0')
            ab.patch.set_linewidth(1)
            ab.patch.set_facecolor('white')
            ax.add_artist(ab)
        else:
            # Fallback to color box if no icon
            border_color = '#333333' if color == '#F6F8FA' else None
            rect = patches.Rectangle((0.02, y_pos - 0.012), 0.03, 0.024, 
                                   linewidth=1 if border_color else 0, 
                                   edgecolor=border_color,
                                   facecolor=color, alpha=0.8,
                                   transform=ax.transAxes)
            ax.add_patch(rect)
        
        # Legend text 
        ax.text(0.07, y_pos, name, transform=ax.transAxes, fontsize=18,
               fontweight='medium', color='#2c3e50', va='center')
    
    # Add clean white background
    ax.set_facecolor('white')
    
    # Tight layout
    plt.tight_layout()
    
    # Save with high DPI
    plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.show()

def plot_commit_breakdown(data, save_path="plots/commit_breakdown_chart.png"):
    """Create a breakdown chart showing co-authored vs primary commits"""
    
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('white')
    
    names = []
    coauthored = []
    primary = []
    
    for user_data in data['users']:
        names.append(user_data['display_name'])
        stats = user_data['overall_stats']
        
        # For Copilot, only show co-authored commits due to primary author data issues
        if user_data['display_name'] == 'Copilot':
            coauthored.append(stats.get('commits_coauthored', 0) or 0)
            primary.append(0)  # Don't show primary author commits for Copilot
        else:
            coauthored.append(stats.get('commits_coauthored', 0) or 0)
            primary.append(stats.get('commits_primary_author', 0) or 0)
    
    # Create stacked bar chart with friendly colors
    x = np.arange(len(names))
    width = 0.6
    
    bars1 = ax.bar(x, coauthored, width, label='Co-authored', 
                   color='#FF6B6B', alpha=0.8, edgecolor='white', linewidth=2)
    bars2 = ax.bar(x, primary, width, bottom=coauthored, label='Primary Author',
                   color='#4ECDC4', alpha=0.8, edgecolor='white', linewidth=2)
    
    # Styling
    ax.set_title('Commit Distribution: Co-authored vs Primary Author', 
                fontsize=22, fontweight='bold', color='#2c3e50', pad=25)
    ax.set_ylabel('Number of Commits', fontsize=20, color='#34495e')
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=18, color='#2c3e50')
    
    # Format y-axis
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1000)}K' if x >= 1000 else str(int(x))))
    
    # Legend
    ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=False)
    
    # Remove spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.show()

def main():
    """Main function to generate all charts"""
    print("Generating AI Assistant GitHub Activity Charts...")
    
    try:
        # Load data
        data = load_data()
        print(f"Loaded data for {len(data['users'])} AI assistants")
        
        # Debug: Check what data we have
        for user in data['users']:
            name = user['display_name']
            weekly_count = len(user['weekly_growth'])
            print(f"  {name}: {weekly_count} weekly data points")
        
        # Generate charts
        print("Creating weekly growth chart...")
        plot_weekly_commits(data)
        
        print("Creating commit breakdown chart...")  
        plot_commit_breakdown(data)
        
        print("All charts generated successfully!")
        
    except FileNotFoundError:
        print("Could not find ai_assistant_github_analysis.json")
        print("   Please run the analysis script first to generate the data.")
    except Exception as e:
        print(f"Error generating charts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
