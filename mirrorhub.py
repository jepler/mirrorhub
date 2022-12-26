#!/usr/bin/env python3
import functools
import itertools
import os
import pathlib
import subprocess
from dataclasses import dataclass, fields

import click
import platformdirs
import requests
import tomlkit
import yaml


@functools.cache
def token():
    with open(platformdirs.user_config_path("gh") / "hosts.yml") as f:
        content = yaml.load(f, yaml.Loader)
    return content["github.com"]["oauth_token"]


@functools.cache
def fieldset(dc):
    return {f.name for f in fields(dc)}


@functools.cache
def fieldset_init(dc):
    return {f.name for f in fields(dc) if f.init}


def dataclass_asdict(dc):
    fs = fieldset(type(dc))
    return {k: getattr(dc, k) for k in fs}


def dataclass_fromdict(dc, /, **kw):
    fs = fieldset_init(dc)
    return dc(**{k: v for k, v in kw.items() if k in fs})


@dataclass
class Settings:
    account_type: str
    name: str


@dataclass
class Options:
    directory: pathlib.Path

    @property
    def config_file(self):
        return self.directory / "mirrorhub.toml"

    @property
    def settings(self):
        if not os.path.exists(self.config_file):
            return
        with self.config_file.open("r", encoding="utf-8") as f:
            return dataclass_fromdict(Settings, **tomlkit.load(f))

    @settings.setter
    def settings(self, new_settings):
        with self.config_file.open("w", encoding="utf-8") as f:
            tomlkit.dump(dataclass_asdict(new_settings), f)


@click.group()
@click.option(
    "--directory",
    "-d",
    type=click.Path(dir_okay=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path("."),
)
@click.pass_context
def cli(ctx, directory):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.obj = Options(directory)


@cli.command
@click.option("--user", "-u", "account_type", flag_value="user", default=True)
@click.option("--organization", "-o", "account_type", flag_value="organization")
@click.argument("name")
@click.pass_context
def init(ctx, account_type, name):
    if ctx.obj.config_file.exists():
        raise RuntimeError("Already a mirrorhub directory")
    ctx.obj.directory.mkdir(parents=True, exist_ok=True)
    ctx.obj.settings = Settings(account_type=account_type, name=name)


def list_remote_repos(settings):
    result = []
    for page in itertools.count(1):
        if settings.account_type == "organization":
            account_api = "orgs"
        else:
            account_api = "users"
        url = f"https://api.github.com/{account_api}/{settings.name}/repos?page={page}"
        headers = {"Authorization": f"Bearer {token()}"}
        #        print(f"# getting {url}")
        with requests.get(url, headers=headers) as req:
            if req.status_code != 200:
                break
            content = req.json()
            #            print(content)
            if not content:
                break
            result.extend(content)
    return result


def list_local_repos(path):
    return [p.parent for p in path.glob("*/.git")]


@cli.command
@click.pass_context
def remote_repos(ctx):
    if ctx.obj.settings is None:
        raise SystemExit("Not a mirrorhub directory")
    for repo in list_remote_repos(ctx.obj.settings):
        print(repo["html_url"])


@cli.command
@click.pass_context
def local_repos(ctx):
    if ctx.obj.settings is None:
        raise SystemExit("Not a mirrorhub directory")
    for repo in list_local_repos(ctx.obj.directory):
        print(repo)


def update_repo(path, clone_url):
    print(f"Updating {path}\n\tfrom {clone_url}")
    if path.exists():
        subprocess.check_call(["git", "--git-dir", path, "fetch", "--tags", "origin"])
    else:
        subprocess.check_call(["git", "clone", "--mirror", clone_url, path])


@cli.command
@click.pass_context
def update(ctx):
    directory = ctx.obj.directory
    if ctx.obj.settings is None:
        raise SystemExit("Not a mirrorhub directory")
    for repo in list_remote_repos(ctx.obj.settings):
        clone_url = repo["clone_url"]
        local_path = ctx.obj.directory / (repo["name"] + ".git")
        if not local_path.is_relative_to(local_path):
            raise SystemExit("Path would be outside base: {local_path}")
        update_repo(local_path, clone_url)


if __name__ == "__main__":
    cli()
