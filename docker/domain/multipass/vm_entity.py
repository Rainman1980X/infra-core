from pydantic import BaseModel, Field

from domain.multipass.vm_type import VmType


class VmEntity(BaseModel):
    vm_instance: str
    vm_type: VmType = Field(default=VmType.MANAGER)  # worker
    ipaddress: str = Field(default="")
    gateway: str = Field(default="")
    memory: str = Field(default="2G")
    disk: str = Field(default="10G")
