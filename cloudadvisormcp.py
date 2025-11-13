from fastmcp import FastMCP
from typing import List,TypedDict
import oci
import logging
from starlette.requests import Request
from starlette.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Advisor(TypedDict, total=False):
    name: str
    resource_type: str
    compartment: str
    region: str
    saving: float

mcp = FastMCP("cloudadvisor")

signer = oci.auth.signers.get_resource_principals_signer()
optimizer_client = oci.optimizer.OptimizerClient(config={},signer=signer)
tenancy_id = signer.tenancy_id

def get_cost_category():
    try:
        list_categories_response = optimizer_client.list_categories(
            compartment_id=tenancy_id,
            compartment_id_in_subtree=True,
            name="cost-management-name")
        return list_categories_response.data.items[0].id
    except Exception as e:
        logger.error(f"Error Fetching category id {str(e)})")
        raise e

def cost_saving_recommendations():
    try:
        list_resource_actions_response = oci.pagination.list_call_get_all_results(optimizer_client.list_resource_actions,
            compartment_id=tenancy_id,
            compartment_id_in_subtree=True,
            include_organization=False,
            limit=1000,
            sort_order="ASC",
            sort_by="NAME",
            lifecycle_state="ACTIVE",
            status="PENDING",
            include_resource_metadata=True)

        response = list_resource_actions_response.data
        return response
    except oci.exceptions.ServiceError as e:
        logger.error(f"Error fetching recommendations: {str(e)}")
        return []

category_id = get_cost_category()

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok", status_code=200)

@mcp.tool()
def cost_optimization() -> List[Advisor]:
    list_of_cost_resources= []
    """It will help with find resources for cost optimization in Oracle Cloud.If user asked for specific resource summarize it only for that resources and not for all.If in doubt always ask the user for more information"""
    cost_response = cost_saving_recommendations()

    for name in cost_response:
        if name.category_id == category_id:
            list_of_cost_resources.append(
                {"name": name.name, "resource_type": name.resource_type, "compartment": name.compartment_name,
                 "region": name.extended_metadata["region"],
                 "saving": name.estimated_cost_saving})

    return list_of_cost_resources


if __name__ == "__main__":
    mcp.run(transport="http",host="<instance_ip>",port=<preferredport>,path="<preferredpath>")
