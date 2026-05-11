"""nyrahost.external.comfyui_workflows — bundled ComfyUI workflow templates.

Templates use ${PLACEHOLDER} substitution (string.Template) for caller-
supplied values. The JSON shape itself MUST be a valid ComfyUI prompt
graph using only node ``class_type`` strings present in the user's
ComfyUI install — ComfyUIClient.run_workflow validates against
GET /object_info before submission.
"""
