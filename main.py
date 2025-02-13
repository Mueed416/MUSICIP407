from highrise import BaseBot, __main__, CurrencyItem, Item, Position, AnchorPosition, SessionMetadata, User
from highrise.__main__ import BotDefinition
from json import load, dump
from emotes import Dance_Floor
import asyncio
import os,shutil
import random
import json
import time

#websocket
import socket
from pytube import YouTube
from urllib.parse import *
import subprocess
from youtubesearchpython import VideosSearch
from pydub import AudioSegment

class Song_Queue:
  def __init__(self, username, song_data, song_file):
    self.username = username
    self.song_data = song_data
    self.song_file = song_file

  def to_dict(self):
    return {
        'username': self.username,
        'song_data': self.song_data,
        'song_file': self.song_file
    }

class Youtube_mp3():
    def __init__(self):
      self.dict = {}
      self.playlist = {}
      self.is_song_play = False
      self.ffmpeg_process = None

    def concat_audio_silent(self, song_file):
      try:
        # Load and convert MP3 files to a common format
      
        audio1 = AudioSegment.from_file("functions/silent.mp3", format="mp3")
        audio2 = AudioSegment.from_file(song_file, format="mp4")

        # # Ensure both audio segments have the same frame rate and channels
        # audio1 = audio1.set_frame_rate(44100).set_channels(2)
        # audio2 = audio2.set_frame_rate(44100).set_channels(2)

        combined = audio1 + audio2 + audio1

        # file name with extension
        file_name = os.path.basename(song_file)

        combined.export(f"./temp_song/output.mp3")
        # print("Merged MP3 files successfully")
        
        return f"./temp_song/output.mp3"
      except FileNotFoundError as e:
        print(f"Error: File not found - {e.filename}")
      except Exception as e:
        print(f"Unexpected error: {e}")
      
      
    async def stream_to_icecast(self, song_file):
      # Define the command to start FFmpeg 
      song_file_with_delay = self.concat_audio_silent(song_file)
      ffmpeg_command = [
        'ffmpeg',
        '-re',         # Read input at native frame rate      
        '-i', song_file_with_delay,
        '-vn',                     # Disable video recording
        '-c:a', 'libmp3lame', 
        # '-c:a', 'aac',  # AAC codec (using libfdk_aac for better quality)
        '-b:a', '128k',  # Bitrate
        '-f', 'mp3',
        '-tune', 'zerolatency',  # Discard corrupt frames
        '-legacy_icecast', '1',
        '-ss', '0',  
        # '-filter_complex', '[0:a]adelay=10000|10000[a]',
        # '-loglevel', 'fatal',
        '-content_type', 'audio/mpeg',  # Set content type for Icecastformat MP3
        'icecast://source:nyCTh81k@link.zeno.fm:80/zvgtsutfmattv'
      ]
      try:    
        self.ffmpeg_process = await asyncio.create_subprocess_exec(
            *ffmpeg_command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        async def read_stream(stream, name):
          while True:
              line = await stream.readline()
              if not line:
                  break
              # print(f"[{name}] {line.decode().strip()}")

        # Read stdout and stderr concurrently
        await asyncio.gather(
          read_stream(self.ffmpeg_process.stdout, "STDOUT"),
          read_stream(self.ffmpeg_process.stderr, "STDERR")
        )

        return_code = await self.ffmpeg_process.wait()
        if return_code != 0:
          print(f"FFmpeg process exited with return code {return_code}")
        else:
          print("Song process completed successfully.")
      except Exception as e:
          print(f"Error while streaming to Icecast: {e}")
      finally:
          self.ffmpeg_process = None

    async def icecast_websocket(self, command, songFile=''):
      if command == "play":
        self.is_song_play = True

        await self.stream_to_icecast(songFile)

        self.is_song_play = False
        print("song play will be false")
      elif command == "stop":
        if self.is_song_play and self.ffmpeg_process:
          self.ffmpeg_process.terminate()
          self.is_song_play = False
          await asyncio.sleep(1)
          try:
            shutil.rmtree("./song")
          except Exception as e:
            print("song folder already removed")
            pass
            print("FFmpeg process stopped")
      elif command == "skip":
        if self.is_song_play and self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            await asyncio.sleep(1)


    def url_search(self, search_query, max_results=3):
      try:
        videos_search = VideosSearch(search_query, max_results)
        result = videos_search.result()
        video_info = result['result'][0]
      except Exception as e:
        print(f"Error searching YouTube: {e}")
        return False


      video_title = video_info['title']
      video_url = video_info['link']

      # Display video details
      print(f"Title: {video_title}")
    
      self.dict[1] = video_url
      print(self.dict)
      return True

    def get_search_items(self, max_search=5):
      if self.dict != {}:
        i = 1
        for url in self.dict.values():
            try:
                yt = YouTube(url)
                title = yt.title
                uploader = yt.author
                duration = yt.length
                views = yt.views
                self.playlist[i] = {'url': url, 'title': title, 'uploader': uploader, 'duration': duration, 'views': views}
                print(f"{i}. Title: {title}")
                print(f"   Uploader: {uploader}")
                print(f"   Duration: {duration} seconds")
                print(f"   Views: {views}")
                return self.playlist[i]
                i += 1
            except Exception as e:
                print(f"Error extracting video info: {e}")
              

    async def play_media(self, url, song_file_name):
      yt = YouTube(url)
      audio_stream = yt.streams.filter(only_audio=True, subtype='mp4').first()
      audio_file = audio_stream.download(filename=song_file_name, output_path='./song', skip_existing=True)
      
      await self.icecast_websocket("play", audio_file)

class Bot(BaseBot):

  def __init__(self):
    super().__init__()
    self.bot_id = None
    self.owner_id = None
    self.bot_status = False
    self.tip_data = None
    self.load_tip_data()
    self.bot_position = None
    self.user_in_room = {}
    self.load_moderators()
    self.admin = 'Tim_Cook'
    self.bot_version = '1.0.0'

    self.youtube_song = Youtube_mp3()
    self.max_song_queue = 10
    self.cooldown_users = {}
    self.load_song_queue()
    self.now_playing = None
        #dance floor position
    min_x = 1
    max_x = 7
    min_y = 0.0
    max_y = 1.5
    min_z = 8.5
    max_z = 13.5

    self.dance_floor_pos = [(min_x, max_x, min_y, max_y, min_z, max_z)]

    #dancer variable
    self.dancer = []

    #dance floor emotes var
    self.emotesdf = Dance_Floor

  def load_moderators(self):
    try:
        with open("moderators.json", "r") as file:
            self.moderators = json.load(file)
    except FileNotFoundError:
        self.moderators = []

    # Add default moderators here
    default_moderators =['Tim_Cook', 'afsuZz']
    for mod in default_moderators:
        if mod.lower() not in self.moderators:
            self.moderators.append(mod.lower())

  def save_moderators(self):
    with open("moderators.json", "w") as file:
        json.dump(self.moderators, file)

  def load_song_queue(self):
    try:
        with open("song_queue.json", "r") as file:
            self.queue_song_list = json.load(file)
            # print(self.queue_song_list)
    except FileNotFoundError:
        self.queue_song_list = []

  def save_song_queue(self):
    with open("song_queue.json", "w") as file:
        json.dump(self.queue_song_list, file)

  def add_to_song_queue(self, user: User, song_data, song_file_name):
    self.queue_song_list.append(Song_Queue(user.username, song_data, song_file_name).to_dict())
    self.save_song_queue()

  def remove_from_song_queue(self, idx):
    self.queue_song_list.pop(idx)
    self.save_song_queue()

  async def play_next(self, is_next=False):
    if self.queue_song_list != []:
      print("Playing next songs..")
      song = self.queue_song_list.pop(0)
      self.save_song_queue()
      self.now_playing = song
      # print(song)
      try:
        if is_next:
          await self.highrise.chat(f" 🎵 Playing next song:\n\n•Title: {song['song_data']['title']}\n•Uploader: {song['song_data']['uploader']}\n•Duration: {song['song_data']['duration']} seconds\n•Requested by: {song['username']}\n\nPlease wait...")
        else:
          await self.highrise.chat(f" 🎵 Playing song:\n\n•Title: {song['song_data']['title']}\n•Uploader: {song['song_data']['uploader']}\n•Duration: {song['song_data']['duration']} seconds\n•Requested by: {song['username']}\n\nPlease wait...")
          
        await self.youtube_song.play_media(song['song_data']['url'], song['song_file'])
      finally:
        await asyncio.sleep(1)
        await self.song_finished(song['song_file'])
    else:
      print("There is no song in queue")

  async def song_finished(self, file_name):
    print("Song finished playing, removing the file")
    try:
      os.remove(f"./song/{file_name}")
    except Exception as e:
      print(f'Failed remove the song: {e}')
    if self.queue_song_list != []:
      await self.play_next(is_next=True)
                                          

  async def on_chat(self, user: User, message: str) -> None:
    print(f"{user.username} said: {message}")
    music_commands_messages = ("-play ", "-p ", "-skip", "-stop", "-queue", "-q", "-now", "-np", "-help")

    if user.username.lower() in self.moderators:
      if message.startswith(music_commands_messages):
        await self.music_commmands(user, message)
    
    response = await self.command_handler(user, message)

    if response:
      try:
        await self.highrise.chat(response)
      except Exception as e:
        print(f"Chat Error: {e}")

  async def music_commmands(self, user: User, message: str) -> None:
    if message.startswith("-play ") or message.startswith("-p "):
      if user.username.lower() in self.moderators or user.username.lower() in self.buyer:
        if (len(self.queue_song_list) >= self.max_song_queue):
          await self.highrise.chat("Queue is full, please wait....")
          return
  
        if user.username in self.cooldown_users:
          still_time = self.cooldown_users[user.username] - time.time()
          time_still_for_user = round(still_time)
          if still_time > 0:
            await self.highrise.send_whisper(user.id, f"You must wait {time_still_for_user}s to use the command again.")
            return
          self.cooldown_users.pop(user.username)
  
        search = None
        if message.startswith("-play "):
          search = message.replace("-play ", "")
        elif message.startswith("-p "):
          search = message.replace("-p ", "")
  
        if search.startswith("http:") or search.startswith("https:"):
          if search.startswith("https://www.youtube.com/watch?v=") or search.startswith("https://youtu.be/"):
            self.youtube_song.dict[1] = search
          else:
            await self.highrise.chat("Please enter a valid YouTube URL")
            return
        else:
          search = self.youtube_song.url_search(search)

          if not search:
            await self.highrise.chat("No songs found, Please try again.")
            return
            
        try:
          song_data = self.youtube_song.get_search_items()
         
          if self.youtube_song.playlist[1]['duration'] > 500:
            await self.highrise.send_whisper(user.id, "Song duration is too long, max is 8 minutes")
            return

          self.cooldown_users[user.username] = time.time() + 20
          song_file_name = user.username + "_" + song_data['title'] + ".mp3"

          self.add_to_song_queue(user, song_data, song_file_name)
          
          if len(self.queue_song_list) == 1 and self.youtube_song.is_song_play is False:
            await self.play_next()
          else:
            await self.highrise.chat(f" ➕ Add song to queue: {self.youtube_song.playlist[1]['title']}.\nRequested by @{user.username}")
            
        except Exception as e:
          if "too many requests" in str(e).lower():
            await self.highrise.chat("Connection unstable, please try again in a moment")
          elif "age restricted" in str(e).lower():
            await self.highrise.chat("Video is age restricted, please try another video")
          else:
            await self.highrise.chat("No songs found, Please try again.")  
          print(f"Error:{e}")

    if user.username.lower() in self.moderators:
      if message.startswith("-stop"):
        self.queue_song_list.clear()
        self.save_song_queue()
        if self.youtube_song.is_song_play is True:
          await self.youtube_song.icecast_websocket("stop")
          await self.highrise.chat(f" ⛔ Stop all song")
        else: 
          await self.highrise.chat("No song playing.")
  
      if message.startswith("-skip"):    
        if self.youtube_song.is_song_play is True:
          await self.youtube_song.icecast_websocket("skip")
          await self.highrise.chat(f" ⏭ Skipping to the next song, please wait...")
        else: 
          await self.highrise.chat("No song playing.")
  
      if message == "-queue" or message == '-q':
        if len(self.queue_song_list) > 0:
          song_names = [f"{i}.{song['song_data']['title']} | Req by @{song['username']}" for i, song in enumerate(self.queue_song_list, start=1)]
          song_names_str = '\n'.join(song_names)
          max_chunk_size = 235
          
          if len(song_names_str) > max_chunk_size:
              # Split the string into chunks
              chunks = [song_names_str[i:i + max_chunk_size] for i in range(0, len(song_names_str), max_chunk_size)]
              for idx, chunk in enumerate(chunks):
                if idx == 0:
                  await self.highrise.chat(f" 🎶 Queue song : \n{chunk}")
                else:
                  await self.highrise.chat(f"{chunk}")
          else:
              # Send the string as a single message
              await self.highrise.chat(f" 🎶 Queue song : \n{song_names_str}")
        else:
          await self.highrise.chat("No song in queue.")
  
      if message == "-now" or message == '-np':
        if self.youtube_song.is_song_play is True:
          song = self.now_playing
          await self.highrise.chat(f" ⏸️ Now playing :\n\n•Title: {song['song_data']['title']}\n•Uploader: {song['song_data']['uploader']}\n•Duration: {song['song_data']['duration']} seconds\n•Requested by: {song['username']}")
        else:
          await self.highrise.chat("No song playing.")

      if message.startswith("-help"):
        await self.highrise.send_whisper(user.id, f" Commands: \n-play <song name> \n-stop \n-queue or -q\n-skip \n-nowp or -np")


  async def on_whisper(self, user: User, message: str) -> None:
    print(f"{user.username} whispered: {message}")
    response = await self.command_handler(user, message)
    if(message.startswith("--")):
      await self.highrise.chat(message.replace("--", ""))
    if response:
      try:
        await self.highrise.send_whisper(user.id, response)
      except Exception as e:
        print(f"Whisper Error: {e}")

  # Handle commands from any source (chat/whisper/message)
  async def command_handler(self, user, message: str):
    command = message.lower().strip()

    # =============================HOST===========================
    if user.id == self.owner_id or user.username.lower() == self.admin.lower():

      if command.startswith("-set"):  # Set the bot at your location
        set_position = await self.set_bot_position(user.id)
      elif command.startswith("-top"):  # Build a 10 top tippers leaderboard
        top_tippers = self.get_top_tippers()
        formatted_tippers = []
        for i, (user.id, user_data) in enumerate(top_tippers):
          username = user_data['username']
          total_tips = user_data['total_tips']
          formatted_tippers.append(f"{i + 1}. {username} ({total_tips}g)")
  
        tipper_message = '\n'.join(formatted_tippers)
        return f"Top Tippers:\n{tipper_message}"
      elif command.startswith("-get "):  # Query a specific user's tips
        username = command.split(" ", 1)[1].replace("@", "")
        tip_amount = self.get_user_tip_amount(username)
        if tip_amount is not None:
          return f"{username} has tipped {tip_amount}g"
        else:
          return f"{username} hasn't tipped."
      elif command.startswith("-wallet"):  # Get Bot wallet gold
        wallet = await self.highrise.get_wallet()
        for currency in wallet.content:
          if currency.type == 'gold':
            gold = currency.amount
            return f"Bot wallet has {gold}g"
        return "No gold in wallet."
      
      elif command.startswith("-mod"):
        username = command.split(" ", 1)[1].replace("@", "")
        await self.highrise.chat(f"{username} is now a 👑Moderator👑, given by {user.username}")
  
        receiver_username = username.lower()
        if receiver_username not in self.moderators:
          self.moderators.append(receiver_username)
          self.save_moderators()
      elif command.startswith("-unmod"):
        username = command.split(" ", 1)[1].replace("@", "")
        await self.highrise.chat(f"{username} is remove from the moderator by {user.username}")
      
        receiver_username = username.lower()
      
    
        # Remove user from moderators list
        if receiver_username in self.moderators:
            self.moderators.remove(receiver_username)
            self.save_moderators()
  
      if message == "-listmod":
        moderators = self.moderators
        moderators_str = ", ".join(moderators)
        max_chunk_size = 240

        if len(moderators_str) > max_chunk_size:
            
            chunks = [moderators_str[i:i + max_chunk_size] for i in range(0, len(moderators_str), max_chunk_size)]
            for idx, chunk in enumerate(chunks):
              if idx == 0:
                await self.highrise.send_whisper(user.id, f"Moderators: {chunk}")
              else:
                await self.highrise.chat(f"{chunk}")
        else:
            await self.highrise.send_whisper(user.id, f"Moderators: {self.moderators}")

      if message == '-reset':
        await self.highrise.send_whisper(user.id, f"Bot reset by {user.username}")
        await self.play_next

      if message == '!botversion':
        await self.highrise.send_whisper(user.id, f"Bot version: {self.bot_version}")
  
      if message.lower().startswith("/buy "):
        parts = message.split(" ")
        if len(parts) != 2:
            await self.highrise.chat("Invalid command")
            return
        item_id = parts[1]
        try:
            response = await self.highrise.buy_item(item_id)
            await self.highrise.chat(f"Item bought: {response}")
        except Exception as e:
            await self.highrise.chat(f"Error: {e}")
  
  
      if message.lower().startswith("/item "):
        parts = message.split(" ")
        if len(parts) < 2:
            await self.highrise.chat("Invalid command")
            return
        item_name = ""
        for part in parts[1:]:
            item_name += part + " "
        item_name = item_name[:-1]
        print (item_name)
        try:
            response = await self.webapi.get_items(item_name=item_name)
            print (response)
        except Exception as e:
            await self.highrise.chat(f"Error: {e}")
  
      if message == "-cc":
        shirt = ["shirt-n_room12019buttondownblack"]
        pant = ["pants-n_room12019formalslacksblack"]
        item_top = random.choice(shirt)
        item_bottom = random.choice(pant)
        xox = await self.highrise.set_outfit(outfit=[
                Item(type='clothing', amount=1, id='body-flesh', account_bound=False, active_palette=0),
                Item(type='clothing', amount=1, id=item_top, account_bound=False, active_palette=1),
                Item(type='clothing', amount=1, id=item_bottom, account_bound=False, active_palette=-1),
                Item(type='clothing', amount=4, id='nose-n_01', account_bound=False, active_palette=4),
                Item(type='clothing', amount=1, id='mouth-basic2018chippermouth', account_bound=False, active_palette=0),
  
                Item(type='clothing', amount=1, id='hair_front-n_malenew18', account_bound=False, active_palette=1),
                Item(type='clothing', amount=1, id='hair_back-n_malenew18', account_bound=False, active_palette=1),
  
                Item(type='clothing', amount=1, id='eyebrow-n_basic2018newbrows14', account_bound=False, active_palette=-0),
                Item(type='clothing', amount=1, id='eye-n_basic2018malesquaresleepy', account_bound=False, active_palette=None),
                Item(type='clothing', amount=1, id='shoes-n_room12019sneakersblack', account_bound=False, active_palette=0),
                Item(type='clothing', amount=1, id='glasses-n_room32019smallshades', active_palette=1),

Item(type='clothing', amount=1, id='freckle-n_basic2018freckle22', account_bound=False, active_palette=-1),

Item(type='clothing', amount=1, id='watch-n_room32019blackwatch')
  
  
        ]) 


  async def on_tip(self, sender: User, receiver: User,
                   tip: CurrencyItem | Item) -> None:
    if isinstance(tip, CurrencyItem):
      print(f"{sender.username} tipped {tip.amount}g -> {receiver.username}")
      if receiver.id == self.bot_id:
        if sender.id not in self.tip_data:
          self.tip_data[sender.id] = {
              "username": sender.username,
              "total_tips": 0
          }

        self.tip_data[sender.id]['total_tips'] += tip.amount
        self.write_tip_data(sender, tip.amount)
        
    
  async def on_user_join(self, user: User,
                         position: Position | AnchorPosition) -> None:
    print(f"{user.username} joined the room")
    self.user_in_room[user.username.lower()] = user.id

  async def on_user_leave(self, user: User) -> None:
    print(f"{user.username} left the room")

  async def on_start(self, session_metadata: SessionMetadata) -> None:
    print("Bot Connected")
    self.bot_id = session_metadata.user_id
    self.owner_id = session_metadata.room_info.owner_id

    # self.highrise.tg.create_task(self.play_next())
    self.highrise.tg.create_task(self.highrise.teleport(self.bot_id, Position(x=11.5, y=1, z=3.5, facing='FrontLeft')))

    asyncio.create_task(self.dance_floor())
    while True:
        await asyncio.sleep(13)
        await self.highrise.send_emote(
     random.choice(['emoji-flex', 'dance-tiktok10','emote-roll', 'emote-superpunch', 'emote-kicking', 'idle-floorsleeping2', 'emote-hero', 'idle_layingdown2', 'idle_layingdown', 'dance-sexy', 'emoji-hadoken', 'emote-disappear', 'emote-graceful', 'sit-idle-cute', 'idle-loop-aerobics', 'dance-orangejustice', 'emote-rest', 'dance-martial-artist', 'dance-breakdance', 'emote-astronaut', 'emote-zombierun', 'idle_singing', 'emote- frollicking', 'emote-float', 'emote-kicking', 'emote-ninjarun', 'emote-secrethandshake', 'emote-apart', 'emote-headball', 'dance-floss', 'emote-jetpack', 'emote-ghost-idle', 'dance-spiritual', 'dance-robotic', 'dance-metal', 'idle-loop-tapdance', 'idle-dance-swinging', 'emote-mindblown', 'emote-gangnam', 'emote-harlemshake', 'emote-robot', 'emote-nightfever', 'dance-anime', 'idle-guitar', 'emote-headblowup', 'dance-creepypuppet', 'emote-creepycute', 'emote-sleigh', 'emote-hyped', 'dance-jinglebell', 'idle-nervous', 'idle-toilet', 'emote-timejump', 'sit-relaxed', 'dance-kawai', 'idle-wild', 'emote-iceskating', 'sit-open', 'dance-touch']))

  # Return the top 10 tippers
  def get_top_tippers(self):
    sorted_tippers = sorted(self.tip_data.items(),
                            key=lambda x: x[1]['total_tips'],
                            reverse=True)
    return sorted_tippers[:10]

  # Return the amount a particular username has tipped
  def get_user_tip_amount(self, username):
    for _, user_data in self.tip_data.items():
      if user_data['username'].lower() == username.lower():
        return user_data['total_tips']
    return None

  # Place bot on start
  async def place_bot(self):
    while self.bot_status is False:
      await asyncio.sleep(0.5)
    try:
      self.bot_position = self.get_bot_position()
      if self.bot_position != Position(0, 0, 0, 'FrontRight'):
        await self.highrise.teleport(self.bot_id, self.bot_position)
        return
    except Exception as e:
      print(f"Error with starting position {e}")

  # Write tip event to file
  def write_tip_data(self, user: User, tip: int) -> None:
    with open("./data.json", "r+") as file:
      data = load(file)
      file.seek(0)
      user_data = data["users"].get(user.id, {
          "total_tips": 0,
          "username": user.username
      })
      user_data["total_tips"] += tip
      user_data["username"] = user.username
      data["users"][user.id] = user_data
      dump(data, file)
      file.truncate()
      
  # Set the bot position at player's location permanently
  async def set_bot_position(self, user_id) -> None:
    position = None
    try:
      room_users = await self.highrise.get_room_users()
      for room_user, pos in room_users.content:
        if user_id == room_user.id:
          if isinstance(pos, Position):
            position = pos

      if position is not None:
        with open("./data.json", "r+") as file:
          data = load(file)
          file.seek(0)
          data["bot_position"] = {
              "x": position.x,
              "y": position.y,
              "z": position.z,
              "facing": position.facing
          }
          dump(data, file)
          file.truncate()
        set_position = Position(position.x, (position.y + 0.0000001),
                                position.z,
                                facing=position.facing)
        await self.highrise.teleport(self.bot_id, set_position)
        await self.highrise.teleport(self.bot_id, position)
        await self.highrise.walk_to(position)
        print(position)
        return "Updated bot position."
      else:
        return "Failed to update bot position."
    except Exception as e:
      print(f"Error setting bot position: {e}")

  async def set_user_position(self, user_id, username) -> None:
      position = None
      try:
        teleport_user_id = None
        room_users = await self.highrise.get_room_users()
        for room_user, pos in room_users.content:
          if user_id == room_user.id:
            if isinstance(pos, Position):
              position = pos
          if username.lower() == room_user.username.lower():
            teleport_user_id = room_user.id

        if position is not None:
          set_position = Position(position.x, (position.y + 0.0000001),
                                  position.z,
                                  facing=position.facing)
          await self.highrise.teleport(teleport_user_id, set_position)
      except Exception as e:
        print(f"Error setting user position: {e}")

  async def dance_floor(self):
      while True:

          try:
              if self.dance_floor_pos and self.dancer:
                  ran = random.randint(1, 73)
                  emote_text, emote_time = await self.get_emote_df(ran)
                  emote_time -= 1

                  tasks = [asyncio.create_task(self.highrise.send_emote(emote_text, user_id)) for user_id in self.dancer]

                  await asyncio.wait(tasks)

                  await asyncio.sleep(emote_time)

              await asyncio.sleep(1)

          except Exception as e:
              print(f"{e}")
      #function to get emote
  async def get_emote_df(self, target) -> None:

      try:
          emote_info = self.emotesdf.get(target)
          return emote_info
      except ValueError:
          pass

  async def on_user_move(self, user: User, destination: Position | AnchorPosition) -> None:
          #get user position on move and add them on self.dancer if on dancefloor
      if user:
  #         # print(f"{user.username}: {destination}")
        if self.dance_floor_pos:
          if isinstance(destination, Position)  :
              for dance_floor_info in self.dance_floor_pos:
                  if (
                    dance_floor_info[0] <= destination.x <= dance_floor_info[1] and
                      dance_floor_info[2] <= destination.y <= dance_floor_info[3] and
                      dance_floor_info[4] <= destination.z <= dance_floor_info[5]
                  ):

                      if user.id not in self.dancer:
                          self.dancer.append(user.id)

                      return
          # If not in any dance floor area
          if user.id in self.dancer:
              self.dancer.remove(user.id)

  # Load tip data on start
  def load_tip_data(self) -> None:
    with open("./data.json", "r") as file:
      data = load(file)
      self.tip_data = data["users"]

  def user_has_tipped(self, user_id: str) -> bool:
    if user_id == self.owner_id:
      return True
    return user_id in self.tip_data

  # Load bot position from file
  def get_bot_position(self) -> Position:
    with open("./data.json", "r") as file:
      data = load(file)
      pos_data = data["bot_position"]
      return Position(pos_data["x"], pos_data["y"], pos_data["z"],
                      pos_data["facing"])


# Automatically create json file if not exists
def data_file(filename: str, default_data: str = "{}") -> None:
  if not os.path.exists(filename):
    with open(filename, 'w') as file:
      file.write(default_data)


DEFAULT_DATA = '{"users": {}, "bot_position": {"x": 0, "y": 0, "z": 0, "facing": "FrontRight"}}'
data_file("./data.json", DEFAULT_DATA)