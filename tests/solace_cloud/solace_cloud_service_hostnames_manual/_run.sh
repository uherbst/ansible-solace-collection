#!/usr/bin/env bash
# Copyright (c) 2022, Solace Corporation, Ricardo Gomez-Ulmke, <ricardo.gomez-ulmke@solace.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

scriptDir=$(cd $(dirname "$0") && pwd);
scriptName=$(basename $(test -L "$0" && readlink "$0" || echo "$0"));
testTarget=${scriptDir##*/}
scriptLogName="$testTargetGroup.$testTarget.$scriptName"
if [ -z "$PROJECT_HOME" ]; then echo ">>> XT_ERROR: - $scriptLogName - missing env var: PROJECT_HOME"; exit 1; fi
source $PROJECT_HOME/.lib/functions.sh

############################################################################################################################
# Environment Variables

  if [ -z "$WORKING_DIR" ]; then echo ">>> XT_ERROR: - $scriptLogName - missing env var: WORKING_DIR"; exit 1; fi
  if [ -z "$LOG_DIR" ]; then echo ">>> XT_ERROR: - $scriptLogName - missing env var: LOG_DIR"; exit 1; fi
  if [ -z "$SOLACE_CLOUD_API_TOKEN_ALL_PERMISSIONS_AU" ]; then echo ">>> XT_ERROR: - $scriptLogName - missing env var: SOLACE_CLOUD_API_TOKEN_ALL_PERMISSIONS_AU"; exit 1; fi
  if [ -z "$FIXED_SOLACE_CLOUD_SERVICE_ID_AU" ]; then echo ">>> XT_ERROR: - $scriptLogName - missing env var: FIXED_SOLACE_CLOUD_SERVICE_ID_AU"; exit 1; fi

##############################################################################################################################
# Settings
export ANSIBLE_SOLACE_LOG_PATH="$LOG_DIR/$scriptLogName.ansible-solace.log"
export ANSIBLE_LOG_PATH="$LOG_DIR/$scriptLogName.ansible.log"

SOLACE_CLOUD_INVENTORY_FILE_NAME="inventory.fixed-service-id.yml"
solaceCloudInventory=$(assertFile $scriptLogName "$scriptDir/$SOLACE_CLOUD_INVENTORY_FILE_NAME") || exit

playbooks=(
  "$scriptDir/main.playbook.yml"
)

##############################################################################################################################
# Run
for playbook in ${playbooks[@]}; do

  playbook=$(assertFile $scriptLogName $playbook) || exit
  ansible-playbook \
                  -i $solaceCloudInventory \
                  $playbook \
                  --extra-vars "WORKING_DIR=$WORKING_DIR" \
                  --extra-vars "SOLACE_CLOUD_API_TOKEN=$SOLACE_CLOUD_API_TOKEN_ALL_PERMISSIONS_AU" \
                  --extra-vars "FIXED_SOLACE_CLOUD_SERVICE_ID=$FIXED_SOLACE_CLOUD_SERVICE_ID_AU"

  code=$?; if [[ $code != 0 ]]; then echo ">>> XT_ERROR - $code - script:$scriptLogName, playbook:$playbook"; exit 1; fi

done

echo ">>> SUCCESS: $scriptLogName"

###
# The End.
