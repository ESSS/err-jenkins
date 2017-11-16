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
conda create -n py36 python=3.6
W:\Miniconda\envs\py36\python.exe -m venv .env36 
.env36\Scripts\activate
```

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

And edit the generated `config.py` with your username instead of `@CHANGE_ME`.

Start it up.

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