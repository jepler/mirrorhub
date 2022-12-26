<!--
SPDX-FileCopyrightText: 2021 Jeff Epler

SPDX-License-Identifier: GPL-3.0-only
-->

# Mirror all of a user or org's repos to the local computer 

Usage:

 * mirrorhub.py \[-d directory\] \[-u|-o\] name
 * mirrorhub.py \[-d directory\] update
 * mirrorhub.py \[-d directory\] local-repos
 * mirrorhub.py \[-d directory\] remote-repos

## Notes

Directly uses the github credentials of the `hub` program, so install & log in
first

Nothing is done for wikis, issue & pull request discussions, etc. It's just the code (though the mirror does include pull request branches)

## Would be nice!

I created this and made it work minimally for my own needs. If it's useful to
you, that's great. I'm not likely to work to directly address issues but will
try to thoughtfully consider pull requests.

Here are some ideas for future directions:

 * update in parallel
 * skip updating repos based on github's reported last update time
 * Correct dependencies in a requirements.txt
 * pip-installable
 * optionally mirror only original repos / selected repos by some criteria
 * private repos support
 * enterprise github support
 * other git hosting support such as gitlab
 * preserving non-git information such as PR discussions, wikis, etc
 * tooling like pre-commit, black, code scanning, etc., to elevate quality
