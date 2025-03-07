from typing import Dict

from domain.command.command_builder.strategies.command_builder_strategy import VmTypeStrategy
from domain.command.command_entity import CommandEntity
from domain.command.command_runner_type_enum import CommandRunnerType
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType
from infrastructure.logging.logger_factory import LoggerFactory
from application.ports.repositories.port_vm_repository import PortVmRepository


class ManagerStrategy(VmTypeStrategy):

    def __init__(self, vm_type: VmType, vm_repository: PortVmRepository = None,command_runner_factory=None):
        super().__init__(vm_type=vm_type,vm_repository=vm_repository,command_runner_factory=command_runner_factory)
        self.logger = LoggerFactory.get_logger(self.__class__)
        self.logger.info("ManagerStrategy initialized")

    def categorize(self, command: CommandEntity, executable_commands: Dict[str, Dict[int, ExecutableCommandEntity]]):
        vm_instance_names = self.vm_repository.find_vm_instances_by_type(self.vm_type)

        if len(vm_instance_names)==1:
            self.logger.info(f"Found vm instance: {vm_instance_names[0]}")
            vm_instance_name = vm_instance_names[0]
            executable_commands.setdefault(vm_instance_name, {})
            executable_commands[vm_instance_name][command.index] =  ExecutableCommandEntity(
            vm_instance_name=vm_instance_name,
            description=command.description.format(vm_instance=vm_instance_name),
            command=command.command.format(vm_instance=vm_instance_name),
            runner=self.command_runner_factory.get_runner(CommandRunnerType.get_enum_from_value(command.runner))
            )
