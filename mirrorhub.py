#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2021 Jeff Epler
# SPDX-License-Identifier: GPL-3.0-only

import functools
import itertools
import os
import pathlib
import subprocess
import traceback
from dataclasses import dataclass, fields
from concurrent.futures import ThreadPoolExecutor
import time

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
    repo_type: str = "all"


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


def request_with_token(url, headers=None, method=requests.get):
    if headers is None:
        headers = {"Authorization": f"Bearer {token()}"}
    else:
        headers.update({"Authorization": f"Bearer {token()}"})
    return method(url, headers)


def paginate(baseurl):
    for page in itertools.count(1):
        add = f"per_page=100&page={page}"
        if "?" in baseurl:
            url = baseurl + "&" + add
        else:
            url = baseurl + "?" + add
        print(f"# getting {url}")
        with request_with_token(url) as req:
            if req.status_code != 200:
                print(f"error {req.status_code=}")
                break
            content = req.json()
            if not content:
                break
            yield from content
            time.sleep(2)


def iter_remote_repos(settings):
    for page in itertools.count(1):
        if settings.account_type == "organization":
            account_api = "orgs"
        else:
            account_api = "users"
        url = f"https://api.github.com/{account_api}/{settings.name}/repos?page={page}&type={settings.repo_type}&per_page=100"
        headers = {"Authorization": f"Bearer {token()}"}
        print(f"# getting {url}")
        with requests.get(url, headers=headers) as req:
            if req.status_code != 200:
                print(f"error {req.status_code}")
                break
            content = req.json()
            if not content:
                break
            yield from content


def list_local_repos(path):
    return [p.parent for p in path.glob("*/.git")]


@cli.command
@click.pass_context
def remote_repos(ctx):
    if ctx.obj.settings is None:
        raise SystemExit("Not a mirrorhub directory")
    for repo in iter_remote_repos(ctx.obj.settings):
        print(repo["html_url"], repo["description"])


@cli.command
@click.pass_context
def local_repos(ctx):
    if ctx.obj.settings is None:
        raise SystemExit("Not a mirrorhub directory")
    for repo in list_local_repos(ctx.obj.directory):
        print(repo)


def update_repo(path, clone_url):
    print(f"Updating {path}\n from {clone_url}")
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

    def inner(repo):
        clone_url = repo["clone_url"]
        local_path = ctx.obj.directory / (repo["name"] + ".git")
        if not local_path.is_relative_to(local_path):
            raise SystemExit("Path would be outside base: {local_path}")
        update_repo(local_path, clone_url)
        description = repo.get("description")
        if description:
            print(f"will set repo description to {description!r}")
            subprocess.check_call(
                [
                    "git",
                    "--git-dir",
                    local_path,
                    "config",
                    "x-mirrorhub.description",
                    description
                ]
            )

    def inner_wrap(repo):
        try:
            inner(repo)
        except Exception as e:
            traceback.print_exc()

    with ThreadPoolExecutor() as pool:
        pool.map(inner_wrap, iter_remote_repos(ctx.obj.settings))


if __name__ == "__main__":
    cli()
