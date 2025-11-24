""" Example: export a YAML workflow to n8n JSON for visualisation. """
from pathlib import Path
from src.integrations.n8n.yaml_to_n8n import yaml_file_to_n8n_json


def main():
    yaml_path = "specs/yaml/order_refund.yaml"
    out_json_path = "order_refund_n8n_workflow.json"
    yaml_file_to_n8n_json(Path(yaml_path), Path(out_json_path))
    print(f"Wrote n8n workflow JSON to: {out_json_path}")



if __name__ == '__main__':
    main()
