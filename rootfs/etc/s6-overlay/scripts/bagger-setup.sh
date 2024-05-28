#!/command/with-contenv bash
# shellcheck shell=bash
set -e

function setup_cron {
    if [[ "${BAGGER_CROND_ENABLE_SERVICE}" == "true" ]]; then
        cat <<EOF | crontab -u nginx -
# min   hour    day     month   weekday command
# ${BAGGER_CROND_SCHEDULE}        cd ${BAGGER_APP_DIR} && ./bin/console app:islandora_bagger:process_queue --queue=${BAGGER_QUEUE_PATH}
${BAGGER_CROND_SCHEDULE}        cd ${LEAF_BAGGER_APP_DIR} && ./venv/bin/python3 leaf-bagger.py --server ${BAGGER_DRUPAL_URL} --output ${LEAF_BAGGER_OUTPUT}/_leaf_bagger_\$(date +"%Y-%m-%dT_%H-%M-%S").csv --container ${OS_CONTAINER}  --date \$(date -d "@$(($(date +%s) - 86400))" +"%Y-%m-%d") && ./venv/bin/python3 leaf-bagger-audit.py --server ${BAGGER_DRUPAL_URL} --output ${LEAF_BAGGER_AUDIT_OUTPUT}/_leaf_bagger_audit_\$(date +"%Y-%m-%dT_%H-%M-%S").csv --container ${OS_CONTAINER} 
EOF
    fi
}

function main {
    setup_cron
}

main
