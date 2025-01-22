import os
import io
import re
import codecs
import base64
import datetime
import tkinter as tk
from PIL import Image
from tkinter import filedialog

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials



# go here: https://developer.spotify.com/dashboard
# to get id and secret
client_id = ""
client_secret = ""

user = ""  # your Spotify user name

def init_sp():
    # spotify scopes: https://developer.spotify.com/documentation/web-api/concepts/scopes
    scope = '''
        playlist-read-private
        playlist-read-collaborative
        playlist-modify-private
        playlist-modify-public
        user-library-read
        user-library-modify
        ugc-image-upload
        user-read-playback-state
        user-modify-playback-state
        user-read-currently-playing
        user-follow-modify
        user-follow-read
        user-read-playback-position
        user-top-read
        user-read-recently-played
        user-read-email
        user-read-private
        '''
    
    # on a new machine, I had to use the first auth_manager, then use the second for subsequent runs
    # I'm not sure why, but it worked.
    # It might be an expiration of the token or something.
    # Figure this out later

    # auth_manager = SpotifyClientCredentials(
    #     client_id=client_id, 
    #     client_secret=client_secret)
    auth_manager = SpotifyOAuth(
        client_id=client_id, 
        client_secret=client_secret, 
        redirect_uri='http://localhost:8000', # this should be the same as the one in the Spotify dashboard
        scope=scope)

    # initialize the spotipy object
    sp = spotipy.Spotify(auth_manager=auth_manager)

    return sp

def create_playlist(sp, playlist_name, user, public=False, collaborateive=False, description=''):
    sp.user_playlist_create(
        user=user, 
        name=playlist_name,
        public=False, 
        collaborative=False, 
        description=description
        )

def list_my_playlists(sp):
    # list my playlists
    playlists = sp.user_playlists(user) # put in the username. Use 'spotify' for spotify's playlists
    # # Uncomment to print the playlists
    # while playlists:
    #     for i, playlist in enumerate(playlists['items']):
    #         print("%4d %s %s %s" % (
    #             i + 1 + playlists['offset'], 
    #             playlist['uri'], 
    #             playlist['name'],
    #             playlist['id']
    #         )
    #         )
    #     if playlists['next']:
    #         playlists = sp.next(playlists)
    #     else:
    #         playlists = None
    return playlists

def update_playlist(sp, track_uris, playlist_id):
    response = sp.playlist_add_items(playlist_id, track_uris)
    if response['snapshot_id']:
        print('tracks added')

def search_tracks(sp, track_list):
    track_uris = []
    found_tracks_count = 0
    not_found_tracks_count = 0

    print()
    print(f"Searching Spotify for {len(track_list)} tracks...")
    print()
    for track in track_list:
        track_name = track['track']
        artist_name = track['artist']
        label_name = track['label']
        album_name = track['album']
        
        # remove "Original Mix" from title
        if "(original mix)" in track_name.lower():
            s = track_name.split("(")
            for phrase in s:
                if "original mix)" in phrase.lower():
                    s.remove(phrase)
            track_name = (" ").join(s).rstrip()

        # create search strings for the tracks. This checks all sorts of combinations of track, artist, album, and label
        # One of these eventually works to find the track on Spotify
        # There is probably a cleaner way to do this...
        # https://support.spotify.com/us/article/search/
        search_str1 = f'track:"{track_name}" artist:"{artist_name}"' 
        search_str2 = f'track:"{track_name}" album:"{album_name}"'
        search_str3 = f'track:"{track_name}" label:"{label_name}"'
        search_str4 = f'track:"{track_name}" artist:"{artist_name}" album:"{album_name}"'
        search_str5 = f'track:"{track_name}" artist:"{artist_name}" label:"{label_name}"'
        search_str6 = f'track:"{track_name}" album:"{album_name}" label:"{label_name}"'
        search_str7 = f'track:"{track_name}" artist:"{artist_name}" album:"{album_name}" label:"{label_name}"'
        search_strs = [search_str1, search_str2, search_str3, search_str4, search_str5, search_str6, search_str7]
        # special case of "feat" in the track name
        if "feat" in track_name:
            track_name_alt = track_name.split("feat")[0].strip()
            artist_name_alt = artist_name + " " + track_name.split("feat")[1].strip()
            search_str8 = f'track:"{track_name_alt}" artist:"{artist_name_alt}"'
            search_str9 = f'track:"{track_name_alt}" album:"{album_name}"'
            search_str10 = f'track:"{track_name_alt}" label:"{label_name}"'
            search_str11 = f'track:"{track_name_alt}" artist:"{artist_name_alt}" album:"{album_name}"'
            search_str12 = f'track:"{track_name_alt}" artist:"{artist_name_alt}" label:"{label_name}"'
            search_str13 = f'track:"{track_name_alt}" album:"{album_name}" label:"{label_name}"'
            search_str14 = f'track:"{track_name_alt}" artist:"{artist_name_alt}" album:"{album_name}" label:"{label_name}"'
            search_strs.extend([search_str8, search_str9, search_str10, search_str11, search_str12, search_str13, search_str14])

        # search for the track
        found_track = False
        for search_str in search_strs:
            result = sp.search(q=search_str, limit=5)
            if len(result['tracks']['items']) > 0:
                track_uri = result['tracks']['items'][0]['uri']
                track_uris.append(track_uri)
                found_tracks_count += 1
                print(f"{found_tracks_count:02} - Found: {track_name} by {artist_name} with search: {search_str}")
                found_track = True
                break
        if not found_track:
            not_found_tracks_count += 1
            print(f"    {not_found_tracks_count:02} - No tracks found for: {track_name}")
            
    print("========================")
    print(f"  Found tracks:     {found_tracks_count}")
    print(f"  Tracks not found: {not_found_tracks_count}")
    print("========================")

    return track_uris

def load_HISTORY_playlist(playlist_number):
    # This just grabs a tracklist from my Rekordbox history playlist
    # You can ignore this, tweak it, or replace it with your own data source
    # It should return three things: track_list, show_date, fun_name
    # 1. track_list is a list of dictionaries with track info like artist, track name, album, label, etc.
    #    The track list contains the info you'll need to search Spotify for the tracks. 
    #    Make sure the track_list has the appropriate search data
    # 2. show_date is a datetime.date object with the date of the show
    # 3. fun_name is a string with the fun name of the show. This is used in the playlist name.
    #    My playlists are saved in the format: "HISTORY Show 524--12-28-24--Vast Landscapes.txt"
    #    The date is Dec 28, 2024. The show number is 524. The fun_name is "Vast Landscapes"
    # The columns of my playlist files are shown below in the comment that shows, "Artwork Track...", etc.

    hisotry_path = "<path to the playlist history directory>"
    
    # find the playlist in the directory
    playlist_file = None
    for file_name in os.listdir(hisotry_path):
        if file_name.endswith(".txt"):
            if len(file_name.split()) > 2:
                if file_name.split()[2].startswith(playlist_number):
                    playlist_file = file_name
                    break
    if playlist_file:
        print(f"Found playlist file: {playlist_file}")
    else:
        print(f"No history file found for HISTORY show {playlist_number}")

    # read the playlist file
    track_list = []
    with codecs.open(os.path.join(hisotry_path, playlist_file), 'r', 'utf-16') as f:
        next(f)  # Skip the first line
        for line in f:
            track_info = line.strip().split('\t')
            if len(track_info) >= 2:
                #	Artwork	Track_Title	Artist Album Label Genre BPM Rating	Time Key Date_Added	Location
                #   1       2           3      4     5     6     7   8      9    10  11         12
                track_dict = {
                    "order": track_info[0],
                    "track": track_info[2], 
                    "artist": track_info[3], 
                    "album": track_info[4],
                    "label": track_info[5],
                    "genre": track_info[6],
                    "bpm": track_info[7],
                    "rating": track_info[8],
                    "time": track_info[9],
                    "key": track_info[10],
                    "date_added": track_info[11],
                    "location": track_info[12]
                }
                track_list.append(track_dict)
                # print(f"{track_dict = }")
    print(f"Track_list length: {len(track_list)}")
    
    # Extract the date from the file name
    show_date = None
    date_pattern = re.compile(r'(\d+)-(\d+)-(\d+)')
    match = date_pattern.search(playlist_file)
    if match:
        month, day, year = match.groups()
        show_date = datetime.datetime.strptime(f"{month}-{day}-{year}", "%m-%d-%y").date()
        print(f"Extracted date: {show_date}")
    else:
        print("No date found in the file name")
    
    # Extract the fun name from the end of the file name
    fun_name = None
    fun_name = playlist_file.split(f"{match.group(0)}")[1].split(".txt")[0]
    # Remove leading spaces and "-" from fun_name
    fun_name = fun_name.lstrip().lstrip("-")
    # Remove leading spaces and "-" from fun_name
    fun_name = fun_name.lstrip().lstrip("-")
    if fun_name:
        print(f"Extracted fun name: {fun_name}")
    else:
        print(f"No fun name found at the end of the file name")

    return track_list, show_date, fun_name

def open_file_dialog():
    # open a dialog to select an image file.
    # This is usually hidden behind all the other windows.
    # Fix this eventually.
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename()
    return file_path

def upload_playlist_image(sp, playlist_id):
    # upload the image. Max file size is 256KB

    # open a file dialog to select the image
    selected_file = open_file_dialog()
    print(f"Selected image file: {selected_file}")

    # upload the image (max size is 256KB)
    try:
        with open(selected_file, 'rb') as image_file:
            image_data = image_file.read()
            # Resize the image to be less than 256KB
            image = Image.open(io.BytesIO(image_data)).convert("RGB")  # Remove alpha channel by converting to RGB
            image.thumbnail((300, 300))  # Resize to a maximum of 300x300 pixels
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)  # Save as JPEG with quality to reduce size
            image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            sp.playlist_upload_cover_image(playlist_id, image_b64)
            print("Image uploaded")

    except Exception as e: 
        print(e)
        print("Image upload failed")

    


if __name__ == '__main__':
    # initialize the spotipy object with credentials, scopes, and stuff
    sp = init_sp()

    # get the show number from the user
    print()
    print("Generate a Spotify playlist from a HISTORY playlist")
    print()
    show_number = input("Enter the show number: ")
    print(f"Show number: {show_number}")
    input("Press Enter to continue...")
    print()
    
    # load the playlist data from the HISTORY file. Get the track list (all data) and show date.
    track_list, show_date, fun_name = load_HISTORY_playlist(show_number)
    playlist_name = f"Best Playlist Eva!"

    # check to see if a playlist exists for the show number
    playlists = list_my_playlists(sp)
    playlist_exists = False
    # if it exists, get the playlist id. If it does, then update the playlist_id
    for playlist in playlists['items']:
        if playlist['name'] == playlist_name:
            playlist_exists = True
            playlist_id = playlist['id']
            print(f"{playlist_name} already exists")
            break

    # if it doesn't exist, create it. Return the playlist_id
    if not playlist_exists:
        description = f"Best Description EVER!"
        create_playlist(sp, playlist_name, description=description, public=True)

        # get the playlist id    
        playlists = list_my_playlists(sp)
        for playlist in playlists['items']:
            if playlist['name'] == playlist_name:
                playlist_id = playlist['id']
                break
    
    # search for the tracks on Spotify and update the playlist
    track_uris = search_tracks(sp, track_list)
    update_playlist(sp, track_uris, playlist_id)

    # upload an image to the playlist
    print()
    print(f"Playlist name: {playlist_name}")
    upload_playlist_image(sp, playlist_id)

    # playlists created by this program are not automatically added to the user's profile
    # I couldn't find a way to programmatically add it to the profile yet.
    print('Playlist created! Remember to add the playlist to your profile.')