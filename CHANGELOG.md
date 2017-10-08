# Gregory
---
### 2017-10-08
#### Added
- The queue is now preserved between restarts of the bot.

#### Changed
- The YTDL config is now `config/ytdl.yml` instead of being hardcoded.
- The audio quality has been droped from `bestaudio/best` to `249/250/140/best`.

#### Removed
---
### 2017-10-07
#### Added
- `reload` commands so we don't have to kill the bot everytime something gets fixed.
- `minewhen` to see when your song will play.
- A few bugfixes and behind the scenes reworking.

#### Changed
- `queue` now shows as many songs as it can fit in one message then truncates the message.
- `remlike` aliased as `dislike` and `unlike`.
- Deaf users don't count towards pausing when the VC is empty.
- Most things now use f strings instead of `.format`.
- Songs must play for 5 seconds before they can be skipped.

#### Removed
---
