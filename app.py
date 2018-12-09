#!/usr/bin/env python3
from flask import *
from requests import post
from json import load, dump
from re import sub
from appdirs import user_config_dir
from os.path import join
from sys import exit

config = {"secret": "gitlab secret token", "token": "bot login token", "port": 25431, "listen": "0.0.0.0"}
config_path = join(user_config_dir(), "gitlab_discord_bridge.json")

try:
    with open(config_path) as f:
        config = json.load(f)
        if config["token"] == "bot login token":
            print("Please update {} with discord bot token".format(config_path))
            exit(2)
except:
    with open(config_path, "w") as f:
        json.dump(config, f)
        print("Please update {} with discord bot token".format(config_path))
        exit(2)


app = Flask(__name__)

def handle_push(body):
    """ Handle GitLab push event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#push-events """
    tcc = body["total_commits_count"]
    commitfmt = "`{id:.7}` **{author[name]}**: {message}"
    body.update({"branch": body["ref"].split("/")[-1],
                 "number": tcc if tcc > 1 else "a",
                 "cmt_plural": "s" if tcc != 1 else "",
                 "commits": "\n".join(commitfmt.format(**c) for c in body["commits"])
                })
    return """:round_pushpin: <{project[web_url]}/commits/{branch}>
**{user_name}** pushed {number} commit{cmt_plural}:
{commits}""".format(**body)

def handle_tag(body):
    """ Handle GitLab tag push event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#tag-events """
    body.update({"tag": body["ref"].split("/")[-1]})
    return """:label: <{project[web_url]}/tree/{tag}>
**{user_name}** pushed a tag: {tag}""".format(**body)

def handle_issue(body):
    """ Handle GitLab issue event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#issues-events """
    try:
        a = body["object_attributes"]["action"]
    except KeyError:
        return False
    if a == "update":
        return False
    body.update({"action": (a + "d") if a[-1] == "e" else (a + "ed")})
    return """:page_facing_up: <{project[web_url]}/issues/{object_attributes[id]}>
**{user[name]}** {action} an issue: {object_attributes[title]}""".format(**body)

def handle_note(body):
    """ Handle GitLab comment (note) event webhook
    https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#comment-events """
    def convert(type):
        s1 = sub('(.)([A-Z][a-z]+)', r'\1 \2', type)
        return sub('([a-z0-9])([A-Z])', r'\1 \2', s1).lower()
    body.update({"type": convert(body["object_attributes"]["noteable_type"]) })
    return """:notepad_spiral: <{object_attributes[url]}>
**{user[name]}** commented on a {type}:
{object_attributes[note]}""".format(**body)

def handle_merge(body):
    """ Handle GitLab merge request event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#merge-request-events """
    if not "url" in body["object_attributes"]:
        body["object_attributes"]["url"] = body["project"]["web_url"] + "/merge_requests"
    return """:arrows_counterclockwise: <{object_attributes[url]}>
**{user[name]}** created a merge request: {object_attributes[source_branch]}->{object_attributes[target_branch]} **{object_attributes[title]}**""".format(**body)

def handle_wiki(body):
    """ Handle GitLab wiki page event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#wiki-page-events """
    return """:notebook: <{object_attributes[url]}>
**{user[name]}** created a wiki page: {object_attributes[title]}""".format(**body)

def handle_pipeline(body):
    """ Handle GitLab pipeline event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#pipeline-events """
    if body["object_attributes"]["status"] == "pending":
        return """:bathtub: {project[web_url]}/pipelines/{object_attributes[id]}
                **{object_attributes[ref]}**: Pipeline created by **{user[name]}**""".format(**body)
    if body["object_attributes"]["status"] == "success":
        return """:bathtub: {project[web_url]}/pipelines/{object_attributes[id]}
                **{object_attributes[ref]}**: Pipeline finished after **{object_attributes[duration]:.0f}** seconds""".format(**body)
    if body["object_attributes"]["status"] == "running":
        return """:bathtub: {project[web_url]}/pipelines/{object_attributes[id]}
                **{object_attributes[ref]}**: Pipeline started""".format(**body)
    return """:bathtub: {project[web_url]}/pipelines/{object_attributes[id]}
            **{object_attributes[ref]}**: Pipeline {object_attributes[status]} after **{object_attributes[duration]:.0f}** seconds""".format(**body)


def handle_build(body):
    """ Handle GitLab pipeline event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#build-events """
    if body["build_status"] == "created":
        return False
    if body["build_status"] == "running":
        body.update({"build_status": "started"})
        return """:robot: <{repository[homepage]}/-/jobs/{build_id}>
                Job **{build_name}** **{build_status}**""".format(**body)
    if body["build_status"] == "success":
        body.update({"build_status": "finished"})
        return """:ok_hand: <{repository[homepage]}/-/jobs/{build_id}>
                Job **{build_name}** **{build_status}** after **{build_duration:.0f}** seconds""".format(**body)
    return """:poop: <{repository[homepage]}/-/jobs/{build_id}>
            Job **{build_name}** **{build_status}** after **{build_duration:.0f}** seconds""".format(**body)

def post_to_discord(channel, text):
    """ Posts to Discord like a boss """
    if text is False:
        return "cool"
    print(text)
    d = post("https://discordapp.com/api/channels/{}/messages".format(channel),
             json={"content": text},
             headers={"Authorization": "Bot " + config["token"],
                      "User-Agent": "gitlab-discord-bridge by blha303"
                     }).json()
    return "cool"

@app.route('/<channelid>', methods=['GET', 'POST'])
def index(channelid):
    if request.method != "POST":
        return make_response("Method Not Allowed", 405)
    if ("host" in config and request.remote_addr != config["host"]) or request.headers.get("X-Gitlab-Token", "") != config["secret"]:
        return make_response("Not Authorized", 403)
    try:
        body = request.get_json()
    except BadRequest:
        return make_response("Bad Request", 400)

    handlers = {"push": handle_push,
                "tag_push": handle_tag,
                "issue": handle_issue,
                "note": handle_note,
                "merge_request": handle_merge,
                "wiki_page": handle_wiki,
                "pipeline": handle_pipeline,
                "build": handle_build
               }
    if body["object_kind"] in handlers:
        return make_response(post_to_discord(channelid, handlers[body["object_kind"]](body) ), 200)
    return make_response("Not Implemented", 501)

if __name__ == "__main__":
    app.run(debug=False, port=config.get("port", 25431), host=config.get("listen", "0.0.0.0"))
