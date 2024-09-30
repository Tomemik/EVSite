<template>
  <v-container>
    <v-card class="mb-4">
      <v-card-title>
        <span class="headline">{{ team.name }}</span>
      </v-card-title>
      <v-card-subtitle>Balance: {{ team.balance.toLocaleString() }} $</v-card-subtitle>
    </v-card>

    <v-card>
      <v-card-title>Inventory</v-card-title>
      <v-data-table
        :headers="additionalInfoHeaders"
        :items="combinedItems"
        item-key="name"
        dense
        class="team-table"
        @click:row="handleRowClick"
      >
        <template v-slot:[`item.tier`]="{ item }">
          <span>{{ item.tier || 'N/A' }}</span>
        </template>
      </v-data-table>

      <v-card-actions>
        <v-btn color="error" @click="openSellTankDialog">Sell Tanks</v-btn>
      </v-card-actions>
    </v-card>

    <V-btn @click="goToManufacturers">Manufacturer</V-btn>

    <!-- Tank Details Dialog -->
    <v-dialog v-model="showTankDetailsDialog" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="headline">{{ selectedTank?.item.name }}</span>
        </v-card-title>
        <v-card-text>
          <div>
            <strong>Battle Rating:</strong> {{ selectedTank?.item.tier }}<br />
            <strong>Quantity:</strong> {{ selectedTank?.item.quantity }}
          </div>
          <v-select
            v-model="selectedUpgrade"
            :items="upgradeOptions"
            item-text="to_tank"
            item-value="upgrade_path_id"
            label="Select an upgrade"
          ></v-select>
          <v-row>
            <v-text-field
              v-model.number="kitQuantities.T1"
              label="Enter Tier 1 Kit Quantity"
              type="number"
              min="0"
              :max=maxKits.T1
              :rules="[value => value >= 0 || 'Invalid quantity']"
            ></v-text-field>
            <v-text-field
              v-model.number="kitQuantities.T2"
              label="Enter Tier 2 Kit Quantity"
              type="number"
              min="0"
              :max=maxKits.T2
              :rules="[value => value >= 0 || 'Invalid quantity']"
            ></v-text-field>
            <v-text-field
              v-model.number="kitQuantities.T3"
              label="Enter Tier 3 Kit Quantity"
              type="number"
              min="0"
              :max=maxKits.T3
              :rules="[value => value >= 0 || 'Invalid quantity']"
            ></v-text-field>
          </v-row>
          <div v-if="selectedUpgradeDetails">
            <div v-if="selectedUpgradeDetails.available_in_manufacturer">
              <strong>Total cost:</strong> {{totalCost}}<br />
              <strong>Available in Manufacturer:</strong> {{ selectedUpgradeDetails.available_in_manufacturer ? 'Yes' : 'No' }}
            </div>
            <div v-else>
              <strong>Total cost:</strong> {{totalCost}}<br />
              <strong>Required Kits:</strong>
              {{
                Object.entries(selectedUpgradeDetails.required_kits).length
                  ? Object.entries(selectedUpgradeDetails.required_kits)
                      .map(([key, value]) => `${key}: ${value}`)
                      .join(', ')
                  : 'None'
              }}<br />
              <strong>Available in Manufacturer:</strong> {{ selectedUpgradeDetails.available_in_manufacturer ? 'Yes' : 'No' }}
            </div>

          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn v-if="isCommander" color="primary" @click="upgradeTank">Upgrade</v-btn>
          <v-btn v-if="isCommander" color="error" @click="sellTank">Sell</v-btn>
          <v-btn @click="showTankDetailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showSellTankDialog" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="headline">Sell Tanks</span>
        </v-card-title>
        <v-card-text>
          <v-form ref="sellTankForm">
            <v-data-table
              :headers="sellTankHeaders"
              :items="filteredTanks"
              item-key="name"
              dense
            >
              <template v-slot:[`item.quantityToSell`]="{ item }">
                <v-text-field
                  v-model.number="sellQuantities[item.name]"
                  :max="item.quantity"
                  label="Quantity"
                  type="number"
                  min="0"
                  :rules="[value => value >= 0 && value <= item.quantity || 'Invalid quantity']"
                ></v-text-field>
              </template>
            </v-data-table>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" @click="sellTanks">Sell</v-btn>
          <v-btn @click="showSellTankDialog = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
import { inject } from "vue";
import {useUserStore} from "../config/store.ts";
import {getAuthToken} from "../config/api/user.ts";
import Manufacturer from "./Manufacturer.vue";

export default {
  components: { Manufacturer },
  data() {
    const $cookies = inject("$cookies");
    const csrfToken = $cookies.get('csrftoken');
    const userStore = useUserStore();
    return {
      csrfToken,
      team: {
        name: '',
        balance: 0,
        tanks: [],
        tank_boxes: [],
        upgrade_kits: {}
      },
      showSellTankDialog: false,
      showTankDetailsDialog: false,
      selectedTank: null,
      selectedUpgrade: null,
      selectedUpgradeDetails: null,
      sellQuantities: {},
      upgradeOptions: [],
      kitQuantities: {
        T1: 0,
        T2: 0,
        T3: 0
      },
      kitValues: {
        T1: 25000,
        T2: 50000,
        T3: 100000,
      },
      baseCost: 0,
      additionalInfoHeaders: [
        { title: 'Name', value: 'name' },
        { title: 'Tier', value: 'tier' },
        { title: 'Quantity', value: 'quantity' }
      ],
      sellTankHeaders: [
        { title: 'Name', value: 'name' },
        { title: 'Tier', value: 'tier' },
        { title: 'Available Quantity', value: 'quantity' },
        { title: 'Quantity to Sell', value: 'quantityToSell' }
      ],
      userStore
    };
  },
  computed: {
    combinedItems() {
      const tankCounts = this.team.tanks.reduce((acc, tank) => {
        acc[tank.tank.name] = acc[tank.tank.name] ? acc[tank.tank.name] + 1 : 1;
        return acc;
      }, {});

      const uniqueTanks = new Set();

      const tanks = this.team.tanks.reduce((acc, tank) => {
        const tankName = tank.tank.name;
        if (!uniqueTanks.has(tankName)) {
          uniqueTanks.add(tankName);
          acc.push({
            name: tankName,
            tier: tank.tank.battle_rating.toFixed(1),
            quantity: tankCounts[tankName]
          });
        }
        return acc;
      }, []);

      const tankBoxes = this.team.tank_boxes.map(box => ({
        name: box.box_name,
        tier: '',
        quantity: box.amount
      }));

      const upgradeKits = Object.keys(this.team.upgrade_kits).map(key => ({
        name: `Upgrade Kit`,
        tier: key,
        quantity: this.team.upgrade_kits[key].quantity
      }));

      return [...tanks, ...tankBoxes, ...upgradeKits];
    },
    filteredTanks() {
      return this.team.tanks.reduce((acc, tank) => {
        const tankName = tank.tank.name;
        const foundTank = acc.find(t => t.name === tankName);
        if (foundTank) {
          foundTank.quantity += 1;
        } else {
          acc.push({
            name: tankName,
            tier: tank.tank.battle_rating.toFixed(1),
            quantity: 1
          });
        }
        return acc;
      }, []);
    },
    maxKits() {
      const maxKits = {
        T1: 0,
        T2: 0,
        T3: 0
      };

      this.combinedItems.forEach(item => {
        if (item.tier === 'T1') {
          maxKits.T1 += item.quantity;
        } else if (item.tier === 'T2') {
          maxKits.T2 += item.quantity;
        } else if (item.tier === 'T3') {
          maxKits.T3 += item.quantity;
        }
      });

      if (this.selectedUpgradeDetails) {
        const requiredKits = this.selectedUpgradeDetails.required_kits;
        console.log(requiredKits)

        for (const tier in requiredKits) {
          if (requiredKits[tier] > 0) {
            maxKits[tier] = Math.max(maxKits[tier] - requiredKits[tier], 0);
          }
        }
      }

      return maxKits;
    },
    totalCost() {
      const tier1Cost = this.kitQuantities.T1 * this.kitValues.T1;
      const tier2Cost = this.kitQuantities.T2 * this.kitValues.T2;
      const tier3Cost = this.kitQuantities.T3 * this.kitValues.T3;
      let new_cost

      const totalKitsCost = tier1Cost + tier2Cost + tier3Cost;
      if (this.selectedUpgradeDetails) {
        if (this.selectedUpgradeDetails.available_in_manufacturer){
          new_cost = Math.max(this.selectedUpgradeDetails.manu_cost - totalKitsCost, 0)
        } else {
          new_cost = Math.max(this.selectedUpgradeDetails.total_cost - totalKitsCost, 0)
        }
      } else {
        new_cost = 0
      }
      return new_cost
    },
    isCommander() {
      return (this.userStore.groups.some(i => i.name === 'commander') &&
             this.userStore.team === this.team.name) || this.userStore.groups.some(i => i.name === 'admin');
    },
  },
  watch: {
    selectedUpgrade(newUpgrade) {
      if (newUpgrade) {
        const upgradeDetails = this.upgradeOptions.find(u => u.to_tank === newUpgrade);
        this.selectedUpgradeDetails = upgradeDetails || null;
        console.log(this.selectedUpgradeDetails.required_kits);
      } else {
        this.selectedUpgradeDetails = null;
      }
    }
  },
  methods: {
    async goToManufacturers() {
      const teamName = this.team.name;
      this.$router.push({ name: 'Manufacturer', params: { TName: teamName } });
    },
    handleRowClick(event, row) {
      this.selectedTank = row;
      this.fetchPossibleUpgrades(row.item.name);
      this.showTankDetailsDialog = true;
      this.kitQuantities.T1 = 0;
      this.kitQuantities.T2 = 0;
      this.kitQuantities.T3 = 0;
    },
    async fetchPossibleUpgrades(tankName) {
      try {
        const response = await fetch(`/api/league/transactions/view_upgrades/`, {
          method: 'GET',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'team': this.team.name,
            'tank': tankName
          }
        });

        if (!response.ok) {
          throw new Error('Error fetching upgrades');
        }

        const upgrades = await response.json();
        console.log(upgrades)
        this.upgradeOptions = upgrades.map(upgrade => ({
          title: upgrade.to_tank,
          upgrade_path_id: upgrade.upgrade_path_id,
          to_tank: upgrade.to_tank,
          total_cost: upgrade.total_cost,
          required_kits: upgrade.required_kits,
          available_in_manufacturer: upgrade.available_in_manufacturer,
          manu_cost: upgrade.manu_cost,
        }));
      } catch (error) {
        console.error("Error fetching possible upgrades:", error);
      }
    },
    async sellTank() {
      if (!this.selectedTank) return;

      const tanksToSell = [{ name: this.selectedTank.item.name, quantity: 1 }];
      console.log(tanksToSell);

      try {
        const response = await fetch('/api/league/transactions/sell_tanks/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'authorization': getAuthToken()
          },
          body: JSON.stringify({
            team: this.team.name,
            tanks: tanksToSell
          })
        });

        if (!response.ok) {
          throw new Error('Error selling tank');
        }

        await this.fetchTeamDetails();
        this.showTankDetailsDialog = false;
      } catch (error) {
        console.error('Error during the sell operation:', error);
      }
    },
    async upgradeTank() {
      if (!this.selectedUpgrade) {
        return;
      }

      try {
        const upgradeDetails = this.upgradeOptions.find(u => u.to_tank === this.selectedUpgrade);
        const response = await fetch('/api/league/transactions/upgrade_tank/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'authorization': getAuthToken()
          },
          body: JSON.stringify({
            team: this.team.name,
            from_tank: this.selectedTank.item.name,
            to_tank: upgradeDetails.to_tank,
            kits: this.kitQuantities
          })
        });

        if (!response.ok) {
          throw new Error("Error upgrading tank");
        }

        await this.fetchTeamDetails();
        this.showTankDetailsDialog = false;
      } catch (error) {
        console.error('Error upgrading tank:', error);
      }
    },
    async fetchTeamDetails() {
      const teamName = this.$route.params.TName;
      try {
        const response = await fetch(`/api/league/teams/${teamName}/`);
        if (!response.ok) {
          throw new Error('Error fetching team details');
        }
        this.team = await response.json();
      } catch (error) {
        console.error('Error fetching team details:', error);
      }
    },
    openSellTankDialog() {
      this.showSellTankDialog = true;
    },
    async sellTanks() {
      const tanksToSell = Object.keys(this.sellQuantities)
        .filter(name => this.sellQuantities[name] > 0)
        .map(name => ({
          name,
          quantity: this.sellQuantities[name]
        }));

      if (tanksToSell.length === 0) return;

      try {
        const response = await fetch('/api/league/transactions/sell_tank/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'authorization': getAuthToken()
          },
          body: JSON.stringify({
            team: this.team.name,
            tanks: tanksToSell
          })
        });

        if (!response.ok) {
          throw new Error('Error selling tanks');
        }

        await this.fetchTeamDetails();
        this.showSellTankDialog = false;
      } catch (error) {
        console.error('Error during the sell operation:', error);
      }
    },
    getMaxKits(tier) {
      console.log(this.combinedItems)
      const tierKits = this.combinedItems.filter(item => item.tier === tier);
      const kitNumber = tierKits.reduce((total, item) => total + item.quantity, 0)
      console.log(kitNumber)
      return ;
    },
  },
  created() {
    this.fetchTeamDetails();
  }
};
</script>

<style scoped>
.team-table {
  cursor: pointer;
}

</style>