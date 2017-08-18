import asyncio
import youtube_dl

from discord import PCMVolumeTransformer, FFmpegPCMAudio

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(PCMVolumeTransformer):
    def __init__(self, source, user, duration, *, data,  volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.user = user
        self.duration = duration
        self.start_time = 0 #idk, super hacky
        self.pause_start = 0
        
        self.skips = []
        self.likes = []

    @classmethod
    async def from_url(cls, url, user=None, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, ytdl.extract_info, url)
        duration = 0
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        
        if 'duration' in data: duration = data['duration']

        filename = ytdl.prepare_filename(data)
        return cls(FFmpegPCMAudio(filename, **ffmpeg_options), user, duration, data=data)
