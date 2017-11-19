# MusicBot

## Commands:
### Categories:

- Bot
- Comp
- Git
- Misc
- Modding
- Music
- Player

#### Bot:

- `!die` - Shuts down the bot
- `!error` - Raises an error. Testing purposes only, please don't use.
- `!join` - Joins a voice channel
- `!joinserver` - Invite the bot to your server
- `!reconnect` - Reconnects the voice client
- `!reload` - Reloads an extension
- `!restart` - Restart the bot
- `!setavatar` - Change the bot's profile picture
- `!setname` - Change the bot's username
- `!setnick` - Change the bot's nickname
- `!summon` - Join the voice channel you're in.

#### Music:

- `!dequeue` - Remove your song(s) from the queue
- `!jingle` - Enqueues a jingle
- `!like` - 'Like' the currently playing song
- `!minewhen` - Tells you when your song will play
- `!mylikes` - Get a list of every song you've ever liked.
- `!np` - Gets the currently playing song
- `!play` - Streams from a url (almost anything youtube_dl supports)
- `!queue` - Shows the current queue.
- `!remall` - Remove all of your songs from the queue
- `!search` - Search for a song
- `!skip` - Registers that you want to skip the current song.
- `!unlike` - Remove your 'like' from a song.
- `!unskip` - Removes your vote to skip the current song.

#### Player:

- `!clear` - Stops player and clears queue
- `!forceskip` - Forcefully skips a song
- `!pause` - Pause the player
- `!resume` - Resumes player
- `!volume` - Changes the player's volume

#### Comp:

- `!cancel_comp` - Cancel any current competitions
- `!end_comp` - End the current competition
- `!start_comp` - Start a competition

#### Git:

- `!git_log` - Shows the latest commits. Defaults to 20 commits.
- `!revert` - Revert local copy to specified commit
- `!update` - Updates the bot from git

#### Misc:

- `!dump_likes` - Get a dump of every like (all time)
- `!help` - This help message
- `!id` - Get your user id
- `!listids` - Get all of the IDs for the current server
- `!most_liked` - Get the top 10 most liked songs of all time
- `!patreon` - Posts info about patreon & the patrons
- `!perms` - View your permissions

#### Modding:

- `!blacklist` - Blacklist a user from using commands
- `!bldump` - Gets a list of every blacklisted user.
- `!remsong` - Remove a song from the queue.



-----------------
## Configuration:

* Edit `config/config.yml` to fit your server's needs
* Put your bot's token in the first line of `config/token.txt`
* Add direct download links (one per line) to jingles in `config/jingles.txt`
* Add the IDs of users (one per line) blacklisted from using commands to `config/blacklist.txt`
* Add the IDs and pledge amounts of users (in YAML format) who are Patrons to `config/patrons.yml`
* Change YouTubeDL settings like audio quality, outfiles, error handling, etc. in `config/ytdl.yml`
* Add links to songs to be played when no-one has queued anything (one per line) to `config/autoplaylist.txt`
* Change the permissions for users and roles in `config/permissions.yml`

-------------------
## Need more help?
DM `Bottersnike#3605` or `hanss314#0128` on Discord.


hey these docs arent finished yet but are good enough I guess?
