#!/bin/sh
PROTOCOL=http
INSTANCE=localhost:3000
TOKEN="$(cat $HOME/.gitea-token)"
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
    i="${i%/}"
    r="$(basename "$i" .git)"
    echo "$i -> $r"
    if ! curl --head -fs "${PROTOCOL}://${INSTANCE}/${UORG}/$r.git" -o /dev/null; then
        # need to create the repo
        curl \
            -X POST "${PROTOCOL}://${INSTANCE}/api/v1/$SCOPE/repos" \
            -H "accept: application/json" \
            -H "Authorization: token $TOKEN" \
            -H "Content-Type: application/json" \
            -d {\"name\":\"$r\"} \
            -i
    fi
    git --git-dir "$i" push --mirror ${PROTOCOL}://$USER:$TOKEN@${INSTANCE}/$UORG/$r.git
done
