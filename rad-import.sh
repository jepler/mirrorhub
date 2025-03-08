#!/bin/sh
USER=jepler
SCOPE=user

while getopts "u:o:" o; do
case "$o" in
    u) USER="${OPTARG}" SCOPE=user ;;
    o) ORG="${OPTARG}"; SCOPE=organization ;;
esac
done

shift $((OPTIND-1))

case "$SCOPE" in
user)
    UORG=$USER ;;
organization)
    SCOPE=orgs/$ORG
    UORG=$ORG ;;
esac

for i in "$@"; do
    if ! [ -e $i/HEAD ]; then echo "$i is not a bare git repository"; continue; fi
    (
        cd $i
        i="${i%/}"
        echo "$i -> $r"
        r="$(basename "$i" .git)"
        if git config remote.rad.url > /dev/null; then
            rad sync
        else
            # radicle limits 
            description="$(printf "%.254s" "$(git config x-mirrorhub.description)")"
            rad init --name "$i" --description "$description" --public --no-confirm
        fi
    )
done
