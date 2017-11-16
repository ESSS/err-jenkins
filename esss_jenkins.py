import random
from fnmatch import fnmatch
from pprint import pformat
from textwrap import dedent
from urllib.parse import urlencode

from errbot import BotPlugin, botcmd, webhook, arg_botcmd
import json

import requests


class ResponseError(Exception):

    def __init__(self, context, response):
        super().__init__('{}: {}'.format(context, response))
        self.response = response


class JenkinsBot(BotPlugin):
    """Jenkins commands tailored to ESSS workflow"""

    def get_configuration_template(self):
        return {
            'JENKINS_TOKEN': '',
            'JENKINS_USERNAME': '',
            'JENKINS_URL': 'https://eden.esss.com.br/jenkins',

            'ROCKETCHAT_USER': '',
            'ROCKETCHAT_PASSWORD': '',
            'ROCKETCHAT_DOMAIN': '',
        }

    def load_user_settings(self, user):
        key = 'user:{}'.format(user)
        settings = {
            'token': '',
            'jobs': [],
            'last_job_listing': [],
        }
        loaded = self.get(key, settings)
        settings.update(loaded)
        self.log.debug('LOAD ({}) settings: {}'.format(user, settings))
        return settings

    def save_user_settings(self, user, settings):
        key = 'user:{}'.format(user)
        self[key] = settings
        self.log.debug('SAVE ({}) settings: {}'.format(user, settings))

    def _generate_job_listing(self, job_names, user):
        items = []
        for (i, job_name) in enumerate(job_names):
            status = self._fetch_job_status(job_name)
            emoji = get_emoji_for_job_status(status)
            if status is not None:
                fmt = '`{index:2d}`. {emoji} [{name}]({url})'
            else:
                fmt = '`{index:2d}`. {emoji} {name}'
            items.append(fmt.format(
                index=i,
                name=job_name,
                url=self._get_job_url(job_name),
                emoji=emoji,
            ))
        settings = self.load_user_settings(user)
        settings['last_job_listing'] = job_names
        self.save_user_settings(user, settings)
        return items

    @botcmd(split_args_with=None, admin_only=True)
    def debug_settings(self, msg, args):
        if not args:
            return 'Enter user name'
        settings = self.load_user_settings(args[0])
        return 'User settings:\n```python\n{}```'.format(pformat(settings))

    @botcmd(split_args_with=None)
    def jenkins_history(self, msg, args):
        """Returns a list with your job history, including running and previous runs."""
        user = args[0] if args else msg.frm.nick
        settings = self.load_user_settings(user)
        infos = settings['jobs']
        if not infos:
            return "You never ran anything. Or at least I don't remember."

        item_texts = self._generate_job_listing([info['job_name'] for info in infos], user)

        s = dedent("""\
            Here you go:
            
            {}
            
            To trigger builds, use `!jenkins build <num1> <num2> <num3> ...`
        """)
        return s.format('\n'.join(item_texts))

    @arg_botcmd('user', type=str)
    @arg_botcmd('--confirm', action='store_true')
    def jenkins_clear(self, msg, user, confirm):
        """Clears your job history."""
        if not confirm:
            return 'Need to pass `--confirm` to this command'
        settings = self.load_user_settings(user)
        settings['jobs'] = []
        self.save_user_settings(user, settings)
        return 'Job history on the trash.'

    @botcmd(split_args_with=None)
    def jenkins_find(self, msg, args):
        """Finds jobs based on keywords, separated by spaces (`ETK 1456 sci20 win64,linux64`)."""
        if not args:
            yield dedent("""\
                Pass some search factors, for example:
                    `ASIM 507 win64,linux64`: matches jobs with `ASIM` *and* `507` *and* ( `win64` *or* `linux64` )                    
                    `"eden-master-win64-35"`: matches exactly the job named `eden-master-win64-35`                    
            """)
            return
        self.log.debug('find from {}: {}'.format(msg.frm.nick, args))

        user = msg.frm.nick
        yield "Hold on, lemme check..."

        all_job_names = self._fetch_all_job_names()
        self.log.debug('found {} jobs in total, filtering by {!r}'.format(len(all_job_names), args))

        job_names = sorted(filter_jobs_by_find_string(all_job_names, args))
        if len(job_names) > 20:
            yield "This resulted in **{}** jobs, which is too much.\n" \
                  "Try to narrow your research.".format(len(job_names))
            return

        if job_names:
            self.log.debug('filtered {} jobs'.format(len(job_names)))
            items = self._generate_job_listing(job_names, user)
            yield dedent("""
                Found these {} jobs:
    
                {}
                
                To trigger builds, use `!jenkins build <num1> <num2> <num3> ...`
            """.format(len(items), '\n'.join(items)))
        else:
            yield "No jobs found, sorry buddy."

        settings = self.load_user_settings(user)
        settings['last_job_listing'] = job_names
        self.save_user_settings(user, settings)

    @botcmd(split_args_with=None)
    def jenkins_build(self, msg, args):
        """Triggers jobs by number from last `!jenkins find` or `!jenkins history` commands"""
        user = msg.frm.nick
        settings = self.load_user_settings(user)
        if not settings['token']:
            return NO_TOKEN_MSG.format(user=user, jenkins_url=self.config['JENKINS_URL'])

        if not settings['last_job_listing']:
            return dedent("""\
                No job listing yet, list jobs first with:
                    `!jenkins history`
                    `!jenkins find <word1> <word2> ...`                    
            """)

        try:
            indexes = [int(x) for x in args]
        except ValueError:
            return "Expected a list of indexes from the previous find command: `!jenkins build <word1> <word2> ...`"

        job_names = [x for (i, x) in enumerate(settings['last_job_listing']) if i in indexes]
        if not job_names:
            return "No jobs selected with those indexes."
        for job_name in job_names:
            self._trigger_job(job_name, user)

        items = ['[{job_name}]({url})'.format(job_name=x, url=self._get_job_url(x)) for x in job_names]
        return dedent("""
            Triggered **{}** jobs:
            
            {}
        """.format(len(items), '\n'.join(items)))

    @botcmd(split_args_with=None)
    def jenkins_token(self, msg, args):
        """Set or get your Jenkins token"""
        user = msg.frm.nick
        settings = self.load_user_settings(user)
        if not args:
            if settings['token']:
                return "You API Token is: `{}` (user: {})".format(settings['token'], user)
            else:
                return NO_TOKEN_MSG.format(user=user, jenkins_url=self.config['JENKINS_URL'])
        else:
            settings['token'] = args[0]
            self.save_user_settings(user, settings)
            return "Token saved."

    @webhook(raw=True)
    def jenkins(self, request):
        """
         {
         'number': '2',
         'job_name': 'fett-master-none-dev-ubuntu16.04-linux-sv01-ci01-execute_cmd',
         'timestamp': '1508516240981',
         'builtOn': 'dev-ubuntu16.04-linux-sv01-ci01',
         'event': 'jenkins.job.started',
         'userId': 'prusse',
         'url': 'job/fett-master-none-dev-ubuntu16.04-linux-sv01-ci01-execute_cmd/2/',
         }
        :param request:
        :return:
        """
        from rocketchat.api import RocketChatAPI
        rocket_api = RocketChatAPI(
            settings={
                'username': self.config['ROCKETCHAT_USER'],
                'password': self.config['ROCKETCHAT_PASSWORD'],
                'domain': self.config['ROCKETCHAT_DOMAIN'],
            }
        )
        self.log.debug('Jenkins: received request: {}'.format(pformat(dict(request.params))))
        info = dict(request.params)

        settings = self.load_user_settings(info['userId'])

        # move this job info to the first position
        infos = settings['jobs']
        for index, existing_info in enumerate(infos):
            if existing_info['job_name'] == info['job_name']:
                del infos[index]
        infos.insert(0, info)

        # keep maximum 10 jobs
        infos = infos[:10]
        settings['jobs'] = infos

        if info['event'] == 'jenkins.job.started':
            template = JOB_STARTED_MSG
            status = ':pray:'
            fmt_kwargs = {'comment': get_job_state_comment('STARTED')}
        else:
            template = JOB_COMPLETED_MSG
            status = ":white_check_mark:" if info['result'] == 'SUCCESS' else ":negative_squared_cross_mark:"
            comment = get_job_state_comment(info['result'])
            info['test_failures'] = self._get_build_test_errors(info['job_name'], info['number'])
            if info['test_failures']:
                max_show = 10
                failures_items = ['**{} failed tests**'.format(len(info['test_failures']))]
                failures_items += ['`{}`'.format(x['name']) for x in info['test_failures'][:max_show]]
                if len(info['test_failures']) > max_show:
                    failures_items.append('... and {} more'.format(len(info['test_failures']) - max_show))
                failures_msg = '\n'.join(failures_items)
            else:
                failures_msg = ''

            fmt_kwargs = {
                'test_failures_msg': failures_msg,
                'comment': comment,
            }

        info['status'] = status
        self.save_user_settings(info['userId'], settings)

        fmt_kwargs['jenkins_url'] = self.config['JENKINS_URL']
        fmt_kwargs.update(info)
        rocket_api.send_message(template.format(**fmt_kwargs).strip(), '@{}'.format(info['userId']))
        return 'OK'

    def _get_job_url(self, job_name):
        return '{}/job/{}'.format(self.config['JENKINS_URL'], job_name)

    def _get_build_test_errors(self, job_name, build_number):
        if build_number is None:
            build_number = 'lastBuild'

        url = 'job/{job_name}/{build_number}/testReport/api/json'.format(job_name=job_name, build_number=build_number)
        try:
            result = self._get_jenkins_json_request(url, params={'tree': 'suites[cases[name,status]]'})
        except ResponseError as e:
            if e.response.status_code == 404:
                return []
            raise
        try:
            cases = result['suites'][0]['cases']
        except:
            self.log.exception('Failed to get cases: {}'.format(url))
            return []

        errors = []
        for case in cases:
            if case['status'] not in ['PASSED', 'SKIPPED', 'FIXED']:
                errors.append(case)

        return errors

    def _fetch_all_job_names(self):
        result = self._get_jenkins_json_request('api/json', params={'tree': 'jobs[fullName]'})
        return [job['fullName'] for job in result['jobs']]

    def _get_jenkins_json_request(self, query_url, params=None):
        """
        returns None if fails to request
        """
        user = self.config['JENKINS_USERNAME']
        token = self.config['JENKINS_TOKEN']
        url = self.config['JENKINS_URL']
        if not url.endswith('/'):
            url += '/'
        url += query_url

        r = requests.get(url, auth=(user, token), params=params)
        if r.status_code not in [200, 201]:
            self.log.debug('_get_jenkins_json_request invalid response: {}'.format(r))
            raise ResponseError('json request to {url}'.format(url=url), r)
        return json.loads(r.text)

    def _fetch_job_status(self, job_name, build=None):
        """
        Fetch the status of the given job name:
        * 'SUCCESS'
        * 'FAILURE'
        * 'ABORTED'
        * 'UNSTABLE'
        * 'NOT_STARTED'
        * 'RUNNING'
        * None: does not exist
        """
        if build is None:
            build = 'lastBuild'
        try:
            response = self._get_jenkins_json_request(
                'job/{job_name}/{build}/api/json'.format(job_name=job_name, build=build),
                params={'tree': 'result'},
            )
        except ResponseError as e:
            # no result yet, check if the job exists then
            if e.response.status_code == 404:
                try:
                    self._get_jenkins_json_request('job/{job_name}/api/json'.format(job_name=job_name))
                    return 'NOT_STARTED'
                except ResponseError as e:
                    if e.response.status_code == 404:
                        return None
                    raise
            raise
        else:
            result = response['result']
            if result is None:
                # response like this: {"_class":"hudson.model.FreeStyleBuild","result":null}
                # means that there's a last build and it is currently running
                result = 'RUNNING'
            return result

    def _get_job_status_emoji(self, job_name):
        return get_emoji_for_job_status(self._fetch_job_status(job_name))

    def _get_job_parameters(self, job_name):
        query_url = 'job/{job_name}/api/json'.format(job_name=job_name)
        result = self._get_jenkins_json_request(query_url, params={'tree': 'actions[parameterDefinitions[name]]'})
        actions = result.get('actions')
        if actions:
            for action in actions:
                parameter_definitions = action.get('parameterDefinitions', [])
                return [p['name'] for p in parameter_definitions]
        return []

    def _get_job_builds(self, job_name):
        result = self._get_jenkins_json_request('job/{}/api/json'.format(job_name), params={'tree': 'builds[number]'})
        if result is None or 'builds' not in result:
            return None

        return [x['number'] for x in result['builds']]

    def _get_job_build_parameters_values(self, job_name, build_number='lastBuild'):
        query = 'job/{}/{}/api/json'.format(job_name, build_number)
        result = self._get_jenkins_json_request(query, params={'tree': 'actions[parameters[name,value]]'})
        actions = result.get('actions', [])
        for action in actions:
            parameters = action.get('parameters')
            if parameters:
                return [(p['name'], p['value']) for p in parameters]
        return []

    def _post_jenkins_json_request(self, post_url, user):
        jenkins_url = self.config['JENKINS_URL']
        token = self.load_user_settings(user)['token']
        if not token:
            raise RuntimeError('Token for user {} not configured'.format(user))

        if not jenkins_url.endswith('/'):
            jenkins_url += '/'

        post_url = jenkins_url + post_url
        r = requests.post(post_url, auth=(user, token))
        self.log.debug('post_jenkins_json_request: url {} = {}'.format(post_url, r.status_code))
        if r.status_code not in (200, 201):
            raise ResponseError('Error posting to {url}: {r}\n{text}'.format(url=post_url, r=r, text=r.text), r)

    def _trigger_job(self, job_name, user):
        builds = self._get_job_builds(job_name)
        parameters = self._get_job_parameters(job_name)

        never_built = not builds
        takes_parameters = bool(parameters)
        if never_built or not takes_parameters:
            post_url = 'job/{}/build' if not parameters else 'job/{}/buildWithParameters'
            post_url = post_url.format(job_name)
            self._post_jenkins_json_request(post_url, user)
        elif takes_parameters:
            parameters_values = self._get_job_build_parameters_values(job_name)
            post_url = 'job/{}/buildWithParameters?{}'.format(job_name, urlencode(parameters_values))
            self._post_jenkins_json_request(post_url, user)


def get_job_state_comment(key):
    comments = COMMENTS.get(key, [key])
    return random.choice(comments)


def get_emoji_for_job_status(result):
    return {
        'SUCCESS': ":white_check_mark:",
        'FAILURE': ":negative_squared_cross_mark:",
        'ABORTED': ":white_circle:",
        'NOT_STARTED': ":white_circle:",
        'UNSTABLE': ":warning:",
        'RUNNING': ":arrows_counterclockwise:",
        None: ":grey_question:",
    }.get(result, result)


def filter_jobs_by_find_string(job_names, input_factors):
    factors = []
    for factor in input_factors:
        if factor.startswith('"') and factor.endswith('"'):
            word = factor[1:-1].lower()
            job_names = [x for x in job_names if fnmatch(x.lower(), word)]
        else:
            factor = factor.lower()
            factors.extend(factor.split('-'))

    and_factors = []
    or_factors = []
    for factor in factors:
        if ',' in factor:
            or_factors.extend(factor.split(','))
        else:
            and_factors.append(factor)

    def matches(fields):
        fields = {x.lower() for x in fields}
        for test_field in and_factors:
            if not any(fnmatch(x, test_field) for x in fields):
                return False
        if not or_factors:
            return True
        for or_factor in or_factors:
            if any(fnmatch(x, or_factor) for x in fields):
                return True

        return False

    return [x for x in job_names if matches(set(x.split('-')))]


COMMENTS = {
    'STARTED': [
        'Now we wait... :popcorn:',
        "Hope it won't take long... ",
        "Coffee maybe? :coffee:",
        "Time to take a break? :smoking:",
    ],
    'SUCCESS': [
        "Way to go! :beer:",
        "Nice! :champagne_glass:",
        "Hooray! :wine_glass:",
    ],
    'FAILURE': [
        "No good...",
        "Tsk tsk tsk...",
        "I feel bad for you... well not really.",
        "Flaky, perhaps?",
    ],
}

NO_TOKEN_MSG = """
**Jenkins API Token not configured**. 
Find your API Token [here]({jenkins_url}/user/{user}/configure) (make sure you are logged in) and execute:

    `!jenkins token <TOKEN>` 

This only needs to be done once.
"""

JOB_STARTED_MSG = '''
**Job Started**!
{status} [{job_name}]({jenkins_url}/{url}) build **{number}**
Building on: **{builtOn}**
'''

JOB_COMPLETED_MSG = '''
**Job Completed**!
{status} [{job_name}]({jenkins_url}/{url}) build **{number}**
{test_failures_msg}
'''
