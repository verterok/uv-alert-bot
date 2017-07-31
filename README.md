
# What's this?

A telegram bot to bridge unifi-video email alerts with telegram notifications/messages in a single group.
It will also send the subject of non-motion alert emails, e.g: cammera disconnect/reconnect

The bot supports 3 commands:

 * /start: tell the bot to send messages to the group where the command is issued, ATM only a single group is supported.
 * /st, /status: show status (active/inactive)
 * /ac, /activate: enable notifications
 * /de, /deactivate: disable notifications, the will receive the email alerts but not forward them to telegram

 in/active state is persistent, and will be maintained across restarts

## Bot setup

 1) create a bot via [BotFather](https://core.telegram.org/bots#6-botfather) and grab the token 
 2) create a group and add your newly created bot to it
 3) create a config based on the [config.yaml.example](config.yaml.example) using the Token and adjust for your system/users
 

### virtualenv 

1) create a virtualenv:

    $ python3 -m venv venv

2) install deps 

    $ source venv/bin/activate 
    $ pip install -r requirements.txt 

3) python ./uv_alert_bot.py config.yaml 

### fades 

1) install [fades](https://pypi.python.org/pypi/fades )

2) run it

    fades ./uv_alert_bot.py config.yaml 

### Docker 

1) docker build . 

2) docker run -v /path/to/config_dir/:/config --net=host

## Unifi video setup

Go to https://your-unifi-video-host:7443/settings/main
  1) enable email alerts 
  2) In the email settings:
     smtp server: IP/hostname where the bot is running
     port: 8025 (or the port you specified in the config.yaml)
  3) save changes 
