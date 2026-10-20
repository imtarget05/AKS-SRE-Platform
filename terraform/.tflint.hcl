# terraform/.tflint.hcl
#
# ONE config for the whole terraform/ tree. tflint runs from the terraform/
# root with --recursive, so this file governs every root below it:
# aks-foundation, modules/acr_attachment, modules/aks_cluster, legacy and
# data-protection. A config that only lives in one root would leave the other
# roots unlinted, which is the failure mode this file exists to prevent.
#
# IMPORTANT: when tflint recurses it resolves the config file RELATIVE TO EACH
# MODULE DIRECTORY. Measured on this tree with tflint v0.64.0:
#   --config "$(pwd)/.tflint.hcl" -> the AzureRM ruleset loads in every root
#                                    (rc=0, 0 issues)
#   --config .tflint.hcl          -> HARD FAIL in all 9 subdirectories
#                                    ("Failed to load TFLint config"), rc=1
#   no --config at all            -> the subdirectories silently fall back to
#                                    the bundled terraform ruleset, where an
#                                    AzureRM finding (a resource missing its
#                                    tags) is MISSED (rc=0)
# Only the absolute path both loads the ruleset everywhere and keeps a missing
# ruleset loud, so the lint is invoked as:
#
#   tflint --recursive --config "$(pwd)/.tflint.hcl" --format=compact
#
# The plugin version is PINNED. An unpinned ruleset means the lint verdict
# changes when upstream cuts a release, so the same commit can pass today and
# fail tomorrow with no diff in this repository. tflint verifies the plugin
# archive checksum on install, so the pin is against substitution, not only
# against typos.
#
# v0.32.0 is the newest release of the AzureRM ruleset and is built against
# tflint-plugin-sdk v0.24.0, which is protocol-compatible with the tflint
# v0.64.0 pinned in .github/workflows/pr-gate.yaml (SDK v0.25.0).
plugin "azurerm" {
  enabled = true
  version = "0.32.0"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

# The bundled "terraform" ruleset stays enabled (tflint enables it
# automatically when the config does not declare a "terraform" plugin block),
# so the terraform-language rules run alongside the AzureRM rules below.
#
# tflint v0.64.0 REMOVED the "preset" block from its config schema, so
# `preset "azurerm" { enabled = true }` is a hard config error on the pinned
# version:
#
#   Failed to load TFLint config; .tflint.hcl:28,1-7: Unsupported block type;
#   Blocks of type "preset" are not expected here.
#
# The modern equivalent of the old preset is "enable the plugin, then switch
# on the rules that ship disabled". Enabling the plugin turns on every rule
# whose Enabled() returns true; the rule below ships disabled and is switched
# on explicitly so the ruleset is not quietly half enabled. The second rule
# already ships enabled and is listed only to make the enforced rule set
# readable from this file alone.
#
# azurerm_resource_missing_tags (NOTICE) ships disabled and REQUIRES the list
# of tag keys a resource must carry. The list is not invented here: it is the
# tagging convention this repository already applies to every taggable Azure
# resource (resource group, AKS cluster, node pool, user-assigned identity):
# environment + owner + purpose.
rule "azurerm_resource_missing_tags" {
  enabled = true
  tags    = ["environment", "owner", "purpose"]
}

# azurerm_resources_missing_prevent_destroy (WARNING) requires prevent_destroy
# on stateful Azure resources (storage, key vault, Cosmos DB, ...). No
# resource of those types exists in this repository today, so the rule reports
# nothing; it is enabled so that the FIRST such resource cannot be created
# destroyable by an accidental apply.
rule "azurerm_resources_missing_prevent_destroy" {
  enabled = true
}
