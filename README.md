# MusicBot

## Commands:
### Categories:

* Bot
* Comp
* Git
* Misc
* Moderation
* Music
* Player

#### Bot:

| Command       | Description                       | Rate | Bucket |
|---------------|-----------------------------------|-----:|-------:|
| `!die`        | Shuts down the bot.               | N/A  | N/A    |
| `!error`      | Raises an error.                  | N/A  | N/A    |
| `!join`       | Joins a voice channel.            | N/A  | N/A    |
| `!joinserver` | Invite the bot to your server.    | N/A  | N/A    |
| `!reconnect`  | Reconnects the voice client.      | N/A  | N/A    |
| `!reload`     | Reloads an extension.             | N/A  | N/A    |
| `!restart`    | Restart the bot.                  | N/A  | N/A    |
| `!setavatar`  | Change the bot's profile picture. | N/A  | N/A    |
| `!setname`    | Change the bot's username.        | N/A  | N/A    |
| `!setnick`    | Change the bot's nickname.        | N/A  | N/A    |
| `!summon`     | Join the voice channel you're in. | N/A  | N/A    |

#### Music:

| Command     | Description                                              | Rate  | Bucket |
|-------------|----------------------------------------------------------|------:|-------:|
| `!dequeue`  | Remove your song(s) from the queue.                      | N/A   | N/A    |
| `!jingle`   | Enqueues a jingle.                                       | 2/15  | User   |
| `!like`     | 'Like' the currently playing song.                       | 2/30  | User   |
| `!minewhen` | Tells you when your song will play.                      | 1/30  | User   |
| `!mylikes`  | Get a list of every song you've ever liked.              | 1/120 | User   |
| `!np`       | Gets the currently playing song.                         | 2/30  | Guild  |
| `!play`     | Streams from a url (almost anything youtube_dl supports. | 2/15  | User   |
| `!queue`    | Shows the current queue.                                 | 1/120 | Guild  |
| `!remall`   | Remove all of your songs from the queue.                 | N/A   | N/A    |
| `!search`   | Search for a song.                                       | 2/15  | User   |
| `!skip`     | Registers that you want to skip the current song.        | 2/30  | User   |
| `!unlike`   | Remove your 'like' from a song.                          | 1/1   | User   |
| `!unskip`   | Removes your vote to skip the current song.              | 2/30  | User   |

#### Player:

| Commmand     | Description                    | Rate | Bucket |
|--------------|--------------------------------|-----:|-------:|
| `!clear`     | Stops player and clears queue. | N/A  | N/A    |
| `!forceskip` | Forcefully skips a song.       | N/A  | N/A    |
| `!pause`     | Pause the player.              | N/A  | N/A    |
| `!resume`    | Resumes player.                | N/A  | N/A    |
| `!volume`    | Changes the player's volume.   | N/A  | N/A    |

#### Comp:

| Commmand       | Description                      | Rate | Bucket |
|----------------|----------------------------------|-----:|-------:|
| `!cancel_comp` | Cancel any current competitions. | N/A  | N/A    |
| `!end_comp`    | End the current competition.     | N/A  | N/A    |
| `!start_comp`  | Start a competition.             | N/A  | N/A    |

#### Git:

| Commmand   | Description                                       | Rate | Bucket |
|------------|---------------------------------------------------|-----:|-------:|
| `!git_log` | Shows the latest commits. Defaults to 20 commits. | N/A  | N/A    |
| `!revert`  | Revert local copy to specified commit.            | N/A  | N/A    |
| `!update`  | Updates the bot from git.                         | N/A  | N/A    |

#### Misc:

| Commmand      | Description                                  | Rate  | Bucket |
|---------------|----------------------------------------------|------:|-------:|
| `!dump_likes` | Get a dump of every like (all time).         | 1/60  | Guild  |
| `!help`       | This help message.                           | 10/15 | User   |
| `!id`         | Get your user id.                            | 1/15  | User   |
| `!listids`    | Get all of the IDs for the current server.   | 1/120 | User   |
| `!most_liked` | Get the top 10 most liked songs of all time. | 4/60  | Guild  |
| `!patreon`    | Posts info about patreon & the patrons.      | 1/10  | Guild  |
| `!perms`      | View your permissions.                       | 1/120 | User   |

#### Modderation:

| Commmand     | Description                            | Rate | Bucket |
|--------------|----------------------------------------|-----:|-------:|
| `!blacklist` | Blacklist a user from using commands.  | N/A  | N/A    |
| `!bldump`    | Gets a list of every blacklisted user. | N/A  | N/A    |
| `!remsong`   | Remove a song from the queue.          | N/A  | N/A    |


## Configuration:

* Edit `config/config.yml` to fit your server's needs
* Put your bot's token in the first line of `config/token.txt`
* Add direct download links (one per line) to jingles in `config/jingles.txt`
* Add the IDs of users (one per line) blacklisted from using commands to `config/blacklist.txt`
* Add the IDs and pledge amounts of users (in YAML format) who are Patrons to `config/patrons.yml`
* Change YouTubeDL settings like audio quality, outfiles, error handling, etc. in `config/ytdl.yml`
* Add links to songs to be played when no|one has queued anything (one per line) to `config/autoplaylist.txt`
* Change the permissions for users and roles in `config/permissions.yml`


## Need more help?
DM `Bottersnike#3605` or `hanss314#0128` on Discord.
