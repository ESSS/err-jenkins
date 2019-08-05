# err-jenkins

[![Travis branch](https://img.shields.io/travis/ESSS/err-jenkins/master.svg)](https://travis-ci.org/ESSS/err-jenkins/)

[errbot plugin](http://errbot.io/en/latest/) to interact with Jenkins, including receiving build notifications.

# Usage

Talk with the bot for help:

```
!help Jenkins
```

# Development

Clone:

```
git clone git@github.com:ESSS/err-jenkins.git
cd err-jenkins
```

Create a virtual environment with Python 3.6 and activate it. Using `conda`:

```
conda install -n root virtualenv
virtualenv .env36
.env36\Scripts\activate
```

**It is important to use a pure virtual environment and not a conda environment**.

Install dependencies:

```
pip install -r dev-requirements.txt
```

Run tests:

```
pytest test_esss_jenkins.py
```

## Run bot in text mode

Create a bot for local development:

```
errbot --init
```

And edit the generated `config.py`:

* Change `@CHANGE_ME` to your username.
* Change `BOT_EXTRA_PLUGIN_DIR` to point to the current directory.

Start it up with:

```
errbot -T
```

To talk with Jenkins you need to configure the bot. Execute:

```
!plugin config Jenkins
{'JENKINS_TOKEN': '',
 'JENKINS_URL': 'https://eden.esss.com.br/jenkins',
 'JENKINS_USERNAME': '',
 'ROCKETCHAT_DOMAIN': '',
 'ROCKETCHAT_PASSWORD': '',
 'ROCKETCHAT_USER': ''}
```

Copy and paste this configuration, setting `JENKINS_TOKEN` and `JENKINS_USERNAME` with your Jenkins user/password or token.
