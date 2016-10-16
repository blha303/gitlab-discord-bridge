_globals = globals
from flask import *

app = Flask(__name__)

def handle_push(body):
    """ Handle GitLab push event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#push-events """
    tcc = body["total_commits_count"]
    outp = { "number": tcc if tcc > 1 else "a",
             "cmt_plural": "s" if tcc != 1 else "",
             "commits": "\n".join("{id:.5} **{author[name]}**: {message}".format(**c) for c in body["commits"])
           }
    return """{project[web_url]}/compare/{before}...{after}
{user_name} pushed {number} commit{cmt_plural}:
{commits}""".format(**outp)

def handle_tag(body):
    """ Handle GitLab tag push event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#tag-events """
    pass

def handle_issue(body):
    """ Handle GitLab issue event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#issues-events """
    pass

def handle_note(body):
    """ Handle GitLab comment (note) event webhook
    https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#comment-events """
    type = body["object_attributes"]["noteable_type"]
    if type == "Commit":
        pass
    elif type == "MergeRequest":
        pass
    elif type == "Issue":
        pass
    elif type == "Snippet":
        pass

def handle_merge(body):
    """ Handle GitLab merge request event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#merge-request-events """
    pass

def handle_wiki(body):
    """ Handle GitLab wiki page event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#wiki-page-events """
    pass

def handle_pipeline(body):
    """ Handle GitLab pipeline event webhook
        https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#pipeline-events """

def post_to_discord(channel, text):
    """ Posts to Discord like a boss """
    pass

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method != "POST":
        return make_response("lol", 400)
    if request.remote_addr != "103.245.212.8":
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
        post_to_discord( handlers[body["object_kind"]](body) )
    return make_response("", 200)
