# Hildegard
---
### 2018-1-13
#### Added
- Website
  - Full queue available on website
  - Mods can remove songs from website


# Leonin
---
### 2017-11-6
#### Added
- Patreon commands and permissions
- Ratelimiting

#### Changed
- Playlists can be queued
- People can queue multiple songs
- Smart dequeueing

#### Removed
---

# Gregory
---
### 2017-10-08
#### Added
- The queue is now preserved between restarts of the bot.

#### Changed
- The YTDL config is now `config/ytdl.yml` instead of being hardcoded.
- The audio quality has been dropped from `bestaudio/best` to `249/250/140/best`.

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
