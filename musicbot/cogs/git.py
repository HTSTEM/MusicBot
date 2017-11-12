import subprocess
import asyncio
import sys
import os

import discord

from discord.ext import commands

from .util import checks
from .util.categories import category


class Git:
    def __init__(self, bot):
        self.bot = bot

    @category('git')
    @commands.command(aliases=['git_pull'])
    async def update(self, ctx):
        '''Updates the bot from git'''

        await ctx.send(':warning: Warning! Pulling from git!')

        if sys.platform == 'win32':
            process = subprocess.run('git pull', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.stdout, process.stderr
        else:
            process = await asyncio.create_subprocess_exec('git', 'pull', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await process.communicate()
        stdout = stdout.decode().splitlines()
        stdout = '\n'.join('+ ' + i for i in stdout)
        stderr = stderr.decode().splitlines()
        stderr = '\n'.join('- ' + i for i in stderr)

        await ctx.send('`Git` response: ```diff\n{}\n{}```'.format(stdout, stderr))
        await ctx.send('These changes will only come into effect next time you restart the bot. Use `{0}die` or `{0}restart` now (or later) to do that.'.format(ctx.prefix))

    @category('git')
    @commands.command()
    async def revert(self, ctx, commit):
        '''Revert local copy to specified commit'''

        await ctx.send(':warning: Warning! Reverting!')

        if sys.platform == 'win32':
            process = subprocess.run('git reset --hard {}'.format(commit), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.stdout, process.stderr
        else:
            process = await asyncio.create_subprocess_exec('git', 'reset', '--hard', commit, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await process.communicate()
        stdout = stdout.decode().splitlines()
        stdout = '\n'.join('+ ' + i for i in stdout)
        stderr = stderr.decode().splitlines()
        stderr = '\n'.join('- ' + i for i in stderr)

        await ctx.send('`Git` response: ```diff\n{}\n{}```'.format(stdout, stderr))
        await ctx.send('These changes will only come into effect next time you restart the bot. Use `{0}die` or `{0}restart` now (or later) to do that.'.format(ctx.prefix))

    @category('git')
    @commands.command(aliases=['gitlog'])
    async def git_log(self, ctx, commits:int = 20):
        '''Shows the latest commits. Defaults to 20 commits.'''

        if sys.platform == 'win32':
            process = subprocess.run('git log --pretty=oneline --abbrev-commit', shell=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.stdout, process.stderr
        else:
            process = await asyncio.create_subprocess_exec('git', 'log', '--pretty=oneline', '--abbrev-commit',
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await process.communicate()
        stdout = stdout.decode().splitlines()
        stdout = '\n'.join('+ ' + i[:90] for i in stdout[:commits])
        stderr = stderr.decode().splitlines()
        stderr = '\n'.join('- ' + i for i in stderr)

        if commits > 10:
            try:
                await ctx.author.send('`Git` response: ```diff\n{}\n{}```'.format(stdout, stderr))
            except discord.errors.HTTPException:
                with open('gitlog.txt', 'w') as log_file:
                    log_file.write('{}\n{}'.format(stdout,stderr))
                with open('gitlog.txt', 'r') as log_file:
                    await ctx.author.send(file=discord.File(log_file))
                os.remove('gitlog.txt')
        else:
            await ctx.send('`Git` response: ```diff\n{}\n{}```'.format(stdout, stderr))


def setup(bot):
    bot.add_cog(Git(bot))
