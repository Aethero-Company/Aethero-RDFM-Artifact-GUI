#!/bin/bash
set -euo pipefail

VERSION="${1:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [[ -z "$VERSION" ]]; then
    echo "Usage: $0 <version-tag>   e.g. $0 v1.2.0" >&2
    exit 1
fi

semver='^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$'
if [[ ! "$VERSION" =~ $semver ]]; then
    echo "ERROR: '$VERSION' is not a valid semver tag (expected vMAJOR.MINOR.PATCH)" >&2
    exit 1
fi

if git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null; then
    echo "ERROR: tag '$VERSION' already exists" >&2
    exit 1
fi

TMP_RELEASE_NOTES=/tmp/release_notes_$1.md
trap 'rm -f "$TMP_RELEASE_NOTES"' EXIT

cp $PROJECT_DIR/release_template.md $TMP_RELEASE_NOTES
code --wait $TMP_RELEASE_NOTES
echo "Done editing"

# --cleanup=whitespace stops git from stripping '#' lines as comments, which
# would otherwise delete every markdown '## heading' from the release notes.
git tag -a --cleanup=whitespace $1 -F $TMP_RELEASE_NOTES
read -rn 1 -p "Tag ready, push now? (y/n) " push
if [[ "$push" == "y" ]]; then
    git push origin $1
else
    echo "Not pushing. You'll have to manually do"
    echo "git push origin $1"
fi
