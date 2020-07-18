import discord
import youtube_dl
import asyncio
import json
youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '/tmp/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    # 'dump_single_json': True,
    'extract_flat': True,
    'playliststart': 1,
    'playlistend': 100,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

# quick one is responisble for enabling the video to play from a playlist quickly
ytdl_quick = youtube_dl.YoutubeDL(ytdl_format_options)
ytdl_format_options["extract_flat"] = False
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
    
    @classmethod
    async def grab_metadata(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=stream))
        return data
    
    @classmethod
    async def check_search(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl_quick.extract_info(url, download=stream))
        for item in data:
            if "ytsearch" in data[item]:
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=stream))
                return data["entries"][0]
        return False

    @classmethod
    async def check_playlist(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl_quick.extract_info(url, download=stream))
        if "entries" not in data:
            return False
        fp = open("test.json", "w")
        json.dump(data, fp, indent=4)
        return data
    
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl_quick.extract_info(url, download=stream))
        
        # fp = open("test.json", "w")
        # json.dump(data, fp, indent=4)
        
        # if 'entries' in data:
        #     # take first item from a playlist
        #     data = data['entries'][0]

        filename = data['url'] if not stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)