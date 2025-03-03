import os
import urllib.request
import shutil

def download_font(url, filename):
    """Download a font file from the given URL"""
    print(f"Downloading {filename}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response, open(filename, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"Successfully downloaded {filename}")
    except Exception as e:
        print(f"Error downloading {filename}: {e}")

def main():
    # Create fonts directory if it doesn't exist
    os.makedirs("assets/fonts", exist_ok=True)
    
    # Font URLs from reliable TTF sources
    fonts = {
        "Roboto-Regular.ttf": "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf",
        "IBMPlexSans-Medium.ttf": "https://raw.githubusercontent.com/IBM/plex/master/IBM-Plex-Sans/fonts/complete/ttf/IBMPlexSans-Medium.ttf",
        "IBMPlexSansCondensed-Bold.ttf": "https://raw.githubusercontent.com/IBM/plex/master/IBM-Plex-Sans-Condensed/fonts/complete/ttf/IBMPlexSansCondensed-Bold.ttf"
    }
    
    # Download each font
    for filename, url in fonts.items():
        filepath = os.path.join("assets/fonts", filename)
        download_font(url, filepath)

if __name__ == "__main__":
    main()