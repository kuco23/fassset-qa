from ..database import DatabaseManager
from ..chain import AssetManager
from ..cmd import AgentBotCli
from ..params import ParamLoader


MINTED_UBA_CORE_VAULT_TRANSFER_THRESHOLD_RATIO = 0.75
MINTED_UBA_CORE_VAULT_RETURN_THRESHOLD_RATIO = 0.2

class AgentLogic:

  def __init__(self, params: ParamLoader, database: DatabaseManager, asset_manager: AssetManager, agent_bot: AgentBotCli):
    self.params = params
    self.database = database
    self.asset_manager = asset_manager
    self.agent_bot = agent_bot

  def create_agent(self, settings_path: str, deposit_for_lots: int = 0, make_available: bool = False):
    agent_vault = self.agent_bot.create_agent(settings_path)
    if deposit_for_lots > 0:
      self.agent_bot.deposit_agent_collaterals(agent_vault, deposit_for_lots)
      if make_available:
        self.agent_bot.make_agent_available(agent_vault)

  def transfer_to_core_vault_if_makes_sense(self, agent_vault: str):
    executing = self.database.agent_executing_transfer_to_core_vault(agent_vault)
    if executing: return
    optimal_transfer_to_core_vault_uba = self.optimal_agent_transfer_to_core_vault_uba(agent_vault)
    optimal_transfer_to_core_vault_lots = self.uba_to_lots(optimal_transfer_to_core_vault_uba)
    if optimal_transfer_to_core_vault_lots > 0:
      print(f'transfering to core vault for agent {agent_vault}')
      self.agent_bot.transfer_to_core_vault(agent_vault, optimal_transfer_to_core_vault_lots)

  def return_from_core_vault_if_makes_sense(self, agent_vault: str):
    optimal_return_from_core_vault_uba = self.optimal_agent_return_from_core_vault_uba(agent_vault)
    optimal_return_from_core_vault_lots = self.uba_to_lots(optimal_return_from_core_vault_uba)
    if optimal_return_from_core_vault_lots > 0:
      print(f'returning from core vault for agent {agent_vault}')
      self.agent_bot.return_from_core_vault(agent_vault, optimal_return_from_core_vault_lots)

  def optimal_agent_transfer_to_core_vault_uba(self, agent_vault: str) -> int:
    """Define the optimal value to transfer to core vault for the given agent"""
    agent_info = self.asset_manager.agent_info(agent_vault)
    minted_uba = agent_info['mintedUBA']
    free_lots = agent_info['freeCollateralLots']
    free_uba = free_lots * self.params.lot_size
    total_uba = free_uba + minted_uba
    if total_uba == 0: return 0

    minted_ratio = minted_uba / total_uba
    if minted_ratio > MINTED_UBA_CORE_VAULT_TRANSFER_THRESHOLD_RATIO:
      _, max_transfer  = self.asset_manager.maximum_transfer_to_core_vault()
      return max_transfer

    return 0

  def optimal_agent_return_from_core_vault_uba(self, agent_vault: str):
    """Define the optimal value to return from core vault for the given agent"""
    agent_info = self.asset_manager.agent_info(agent_vault)
    minted_uba = agent_info['mintedUBA']
    free_lots = agent_info['freeCollateralLots']
    free_uba = free_lots * self.params.lot_size
    total_uba = free_uba + minted_uba
    if total_uba == 0: return 0

    minted_ratio = minted_uba / total_uba
    if minted_ratio < MINTED_UBA_CORE_VAULT_RETURN_THRESHOLD_RATIO:
      _, core_vault_balance = self.asset_manager.core_vault_available_amount()
      return min(core_vault_balance, free_uba)

    return 0

  def uba_to_lots(self, amount: int):
    return amount / self.params.lot_size
