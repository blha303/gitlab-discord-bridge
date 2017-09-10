#!/usr/bin/env python3
from flask import *
from requests import post
from json import load, dump
from re import sub

with open("config.json") as f:
    config = json.load(f)

app = Flask(__name__)

def handle_push(body):
    """ Handle GitLab push event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#push-events """
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
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#tag-events """
    body.update({"tag": body["ref"].split("/")[-1]})
    return """:label: <{project[web_url]}/tree/{tag}>
**{user_name}** pushed a tag: {tag}""".format(**body)

def handle_issue(body):
    """ Handle GitLab issue event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#issues-events """
    print(body)
    try:
        a = body["object_attributes"]["action"]
    except KeyError:
        a = "Touch"
    if a == "update":
        return False
    body.update({"action": (a + "d") if a[-1] == "e" else (a + "ed")})
    return """:page_facing_up: <{project[web_url]}/issues/{object_attributes[id]}>
**{user[name]}** {action} an issue: {object_attributes[title]}""".format(**body)

def handle_note(body):
    """ Handle GitLab comment (note) event webhook
    https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#comment-events """
    def convert(type):
        s1 = sub('(.)([A-Z][a-z]+)', r'\1 \2', type)
        return sub('([a-z0-9])([A-Z])', r'\1 \2', s1).lower()
    body.update({"type": convert(body["object_attributes"]["noteable_type"]) })
    return """:notepad_spiral: <{object_attributes[url]}>
**{user[name]}** commented on a {type}:
{object_attributes[note]}""".format(**body)

def handle_merge(body):
    """ Handle GitLab merge request event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/user/project/integrations/webhooks.md#push-events """
    try:
        url=body["object_attributes"]["url"]
    except KeyError:
        url=body["project"]["web_url"] + "/merge_requests"
    body["object_attributes"]["url"]=url
    return """:arrows_counterclockwise: <{object_attributes[url]}>
**{user[name]}** created a merge request: {object_attributes[source_branch]}->{object_attributes[target_branch]} **{object_attributes[title]}**""".format(**body)

def handle_wiki(body):
    """ Handle GitLab wiki page event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#wiki-page-events """
    return """:notebook: <{object_attributes[url]}>
**{user[name]}** created a wiki page: {object_attributes[title]}""".format(**body)

def handle_pipeline(body):
    """ Handle GitLab pipeline event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#pipeline-events """
    # i don't even know what to put here
    print(body)
    return ":bathtub: Someone tried to do something with a pipeline :P"

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
        return make_response("lol", 400)
    if ("host" in config and request.remote_addr != config["host"]) or request.headers.get("X-Gitlab-Token", "") != config["secret"]:
        return make_response("go away please", 403)
    try:
        body = request.get_json()
    except BadRequest:
        return make_response("lol", 400)

    handlers = {"push": handle_push,
                "tag_push": handle_tag,
                "issue": handle_issue,
                "note": handle_note,
                "merge_request": handle_merge,
                "wiki_page": handle_wiki,
                "pipeline": handle_pipeline
               }
    if body["object_kind"] in handlers:
        return make_response(post_to_discord(channelid, handlers[body["object_kind"]](body) ), 200)
    return make_response("wat", 400)

if __name__ == "__main__":
    app.run(debug=False, port=25431, host="0.0.0.0")
