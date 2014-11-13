This is a tool in Python that can fetch the entirety of a Google Group as raw mbox files for easy import into other systems.

Since there is no native way offered by Google to do that, we have to spider the web interface and extract all the messages manually.

# Features

* Fetches all messages in all topics as individual mbox files (one directory per group, one subdirectory per topic, one file per message)
* Can operate on private groups by using lynx' cookie store
* Incremental update mode using RSS
* Postprocessing tool `demangle.py` that fixes two sorts of message munging that google applies (probably a bug on their side).

# Quickstart

## Public group

````
./src/gggd.py group-name
````

And at a later point to update using the RSS of the latest 50 messages:

````
./src/gggd.py -u group-name
````

## Restricted group/Full member addresses

Depending on your lynx configuration you will not be able to access restricted groups this way. Also: all email addresses in all messages will be mangled to protect against address harvesting. Both problems can be solved by logging into a Google account with access to the group. (Getting full email addresses may need additional permissions.)

````
./src/gggd.py -l -C cookies group-name
````

will open an interactive lynx session in which you should log-in to your Google account. The session cookies are stored in the `cookies` file. You can move around form fields with the up and down arrow keys, submit a form with the right arrow or enter keys, and exit lynx by pressing the letter `q` (and confirming) when not in a text input field. Afterwards a normal fetch (now using the logged-in account) will be performed.

To update based on the RSS feed (and with the existing `cookies` file):

````
./src/gggd.py -u -C cookies group-name
````

## Data de-mangling

By default gggd retrieves the 'raw message's as they are returned by the Google Groups API. In my tests these have two types of errors:
* Some messages get two RFC (2)822 headers. The second one seems to be a proper superset of the first one with added "X-Google-\*"-headers.
* Messages with multiple levels of MIME (e.g. mixed( alternative(text, html), pdf)) seem to always lose their first inner MIME header, leading to wrong parsing.

The supplied `demangle.py` tool can apply heuristics to detect both of these problems and try to fix the message to get into a shape that resembles what it looked like before the modifications. This should allow all messages to be properly parsed again by all software. Warning: Since the modification cannot be reverted exactly, message signatures are likely to break in the process.

````
find group-name -type f | xargs ./src/demangle.py
````

will look for all files in the `group-name` folder (as previously downloaded by gggd.py) and write a fixed version with suffix "`.demangled`" next to each file (regardless of whether demangling was necessary or not, in the latter case the file will be identical to the original).

Alternatively the option `-d` to `gggd.py` will apply the de-mangling step inline, after downloading and before writing each file. This works with both initial downloads and RSS based updates.

# Lynx configuration

The `gggd` tool will look for and use a lynx configuration file in `.lynxrc` in the current user's home directory. If that file doesn't exist, a warning is issued in verbose mode and lynx is called with no explicit configuration, falling back to whatever the system default configuration is.

In order for `gggd` to be able to act as a logged-in user (allowing to access non-public groups and full sender email addresses if the logged-in user is a group administrator), lynx must be provided with Google session cookies. This can be achieved in three different ways:

## Create local cookie file

When calling `gggd` with the `-C cookie` option (where `cookie` is a file name), lynx will be configured with all necessary options to make `cookie` a file that stores cookies. You can use the option `-l` (log-in and then proceed with the normal operations, i.e. fetch or update) or `-L` (log-in and then exit, e.g. to prepare a file for unattended operation) to `gggd` to call up an interative lynx session with the correct cookie configuration in which you can log in to a Google account.

Note: Due to a limit in the lynx parameter passing (the `PERSISTENT_COOKIES` option can only be set at compile time or in a configuration file), this mode of operation utilizes a temporary lynx configuration file.

## Create a user cookie file

If you don't want to always have to pass the `-C cookie` option you can create a lynx configuration file in `${HOME}/.lynxrc` and configure this for permanent cookies. Lynx *will not* read more than one configuration, so using a custom configuration file will *replace* all system defaults. For this reason it's recommended to create the file like so:

````
lynx -show_cfg > .lynxrc
````

which will dump the current configuration into the file. Then you can use any editor to update the file and add the following configuration items to the end:

````
SET_COOKIES:TRUE
ACCEPT_ALL_COOKIES:TRUE
PERSISTENT_COOKIES:TRUE
COOKIE_FILE:~/.lynx_cookies
COOKIE_SAVE_FILE:~/.lynx_cookies
````

(you may customize the `COOKIE_FILE` and `COOKIE_SAVE_FILE` parameters, but they should point to the same file). Afterwards you can get Google Group session cookies by visiting the login form with this configuration file:

````
lynx -cfg "${HOME}/.lynxrc" "https://www.google.com/a/UniversalLogin?continue=https://groups.google.com/forum/&service=groups2&hd=default"
````

Tip: Using
````
alias lynx="lynx -cfg=$HOME/.lynxrc"
````
e.g. in your `.bash_aliases` you can use this configuration for all lynx calls from the shell.

## Using an existing cookie file

Both the `-C cookie` and the `-c config` options can be used with cookie files prepared externally. This is out of the scope of this document, see the lynx documentation. Note that in case of an existing fully filled cookie file you only need the `SET_COOKIES` and `COOKIE_FILE` configuration options.

# Full option set

FIXME

# mbox conversion and mailman import

FIXME

# Theory of operation
The basic ideas of the software are adapted from https://github.com/icy/google-group-crawler with important distinctions: This project is in Python which is easier to read and adapt, and it uses lynx with a configuration file for all operations which allows to access protected groups (lynx needs to be manually logged in to a Google account with group access first).

Google Groups has three layers of hierarchy: A group has multiple topics, a topic has multiple messages. The group is identified by its name, topics and messages are identified by alphanumeric identifiers.

The URLs retrieved are:
* `https://groups.google.com/forum/?_escaped_fragment_=forum/GROUP_NAME` which returns an overview page with links to `https://groups.google.com/d/topic/GROUP_NAME/TOPIC_ID` listing a number of topic IDs and possibly a link to the next page looking something like `https://groups.google.com/forum/?_escaped_fragment_=forum/GROUP_NAME[21-40-false]`. All the next page links are followed until no next page is found.
* `https://groups.google.com/forum/?_escaped_fragment_=topic/GROUP_NAME/TOPIC_ID` which returns a message overview with links to `https://groups.google.com/d/msg/GROUP_NAME/TOPIC_ID/MESSAGE_ID` listing all message IDs.
* `https://groups.google.com/forum/message/raw?msg=GROUP_NAME/TOPIC_ID/MESSAGE_ID` which returns the actual message in mbox format (with some brokenness, see Data de-mangling).
* `https://groups.google.com/forum/feed/GROUP_NAME/msgs/rss.xml?num=MESSAGE_COUNT` which returns an RSS file with the last MESSAGE_COUNT messages. A link to each message of the form `https://groups.google.com/d/msg/GROUP_NAME/TOPIC_ID/MESSAGE_ID` (giving topic and message ID) is in the `<link>` element of each `<item>`
 