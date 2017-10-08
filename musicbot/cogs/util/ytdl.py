import asyncio
import logging
import youtube_dl

from ruamel.yaml import YAML
from discord import PCMVolumeTransformer, FFmpegPCMAudio

yaml = YAML(typ='safe')
with open('config/ytdl.yml') as conf_file:
    ytdl_format_options = yaml.load(conf_file)

ffmpeg_options = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)



def cleanup(self):
    log = logging.getLogger('discord.player')

    proc = self._process
    if proc is None:
        return

    log.debug('Preparing to terminate ffmpeg process %s.', proc.pid)
    proc.kill()
    if proc.poll() is None:
        log.debug('ffmpeg process %s has not terminated. Waiting to terminate...', proc.pid)
        proc.communicate()
        log.debug('ffmpeg process %s should have terminated with a return code of %s.', proc.pid, proc.returncode)
    else:
        log.debug('ffmpeg process %s successfully terminated with return code of %s.', proc.pid, proc.returncode)

    self._process = None        
FFmpegPCMAudio.cleanup = cleanup


class YTDLSource(PCMVolumeTransformer):
    def __init__(self, source, user, duration, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.user = user
        self.duration = duration
        self.start_time = 0 #idk, super hacky
        self.pause_start = 0

        self.channel = None
        self.skips = []
        self.likes = []

    @classmethod
    async def get_duration(cls, url, user=None, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda:ytdl.extract_info(url, download=False))
        duration = 0
        if 'entries' in data and data['entries']:
            # take first item from a playlist
            data = data['entries'][0]

        if 'duration' in data: duration = data['duration']

        return duration

    @classmethod
    async def from_url(cls, url, user=None, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, ytdl.extract_info, url)
        duration = 0
        if 'entries' in data and data['entries']:
            # take first item from a playlist
            data = data['entries'][0]

        if 'duration' in data: duration = data['duration']

        filename = ytdl.prepare_filename(data)
        return cls(FFmpegPCMAudio(filename, **ffmpeg_options), user, duration, data=data)

    @classmethod
    async def search(cls, query, *args, **kwargs):
        return ytdl.extract_info(query, *args, **kwargs)
    
    #produces a fresh copy
    def duplicate(self):
        return YTDLSource(
            FFmpegPCMAudio(ytdl.prepare_filename(self.data), **ffmpeg_options), 
            self.user, self.duration, data=self.data)
    
