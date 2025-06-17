#!/bin/bash
###############################################################################################################################
# Variables
###############################################################################################################################
REGISTRY=""
REGISTRY_NAMESPACE=""

###############################################################################################################################
# Functions
###############################################################################################################################
# Informational Functions
usage() {
cat << EOF

usage: ${SCRIPT_NAME} [options]

This script exports data from one database to be compared with data from another database

OPTIONS:
    -h      Show this message
    -v      Version to build, defaults to 'latest'
    -f      Custom Containerfile with absolute or relative directory
    -F      Format of containerfile
EOF
exit 1
}

get_parameters() {
    while getopts "f:F:hRSv:" option_name; do
        case "$option_name" in
            "f")
                OPT_CONTAINERFILE="$OPTARG"
                ;;
            "F")
                OPT_FORMAT_TYPE="$OPTARG"
                ;;
            "h")
                usage
                ;;
            "v")
                OPT_VERSION="$OPTARG"
                ;;
            "?")
                echo "Error: Unknown option $OPTARG"
                usage
                ;;
            ":")
                echo "Error: No argument value for option $OPTARG"
                usage
                ;;
            *)
                echo "Error: Unknown error while processing options"
                usage
                ;;
        esac
    done

    if [[ -z $OPT_CONTAINERFILE ]]; then
        OPT_CONTAINERFILE="docker/Containerfile"
    fi

    if [[ -z $OPT_FORMAT_TYPE ]]; then
        OPT_FORMAT="--format docker"
    elif [[ $OPT_FORMAT_TYPE == "podman" ]]; then
        OPT_FORMAT=""
    else
        OPT_FORMAT="--format ${OPT_FORMAT_TYPE}"
    fi

    if [[ -z $OPT_VERSION ]]; then
        OPT_VERSION="latest"
    fi
}

# Build Functions
container_build() {
    if [[ -z $TAG ]]; then
        podman login ${REGISTRY}
        podman build -f ${OPT_CONTAINERFILE} -t ${REGISTRY}/${REGISTRY_NAMESPACE}:latest
        podman push ${REGISTRY}/${REGISTRY_NAMESPACE}:latest
    else
        podman build -f ${OPT_CONTAINERFILE} -t ${REGISTRY}/${REGISTRY_NAMESPACE}:${TAG} -t ${REGISTRY}/${REGISTRY_NAMESPACE}:latest
        podman push ${REGISTRY}/${REGISTRY_NAMESPACE}:${TAG}
        podman push ${REGISTRY}/${REGISTRY_NAMESPACE}:latest
    fi
}

###############################################################################################################################
# Main Script
###############################################################################################################################
get_parameters "$@"

container_build
