<template>
  <v-container>
    <v-card class="mb-4">
      <v-card-title>
        <span class="headline">{{ team.name }}</span>
      </v-card-title>
      <v-card-subtitle>Balance: {{ team.balance.toLocaleString() }} $</v-card-subtitle>
    </v-card>

    <V-btn @click="goToManufacturers" style="margin-top: 10px; margin-bottom: 10px; margin-right: 10px">Manufacturer</V-btn>
    <V-btn v-if="(userStore.groups.some(i => i.name === 'commander') &&
             userStore.team === team.name) || userStore.groups.some(i => i.name === 'admin')" @click="showTransferDialog=true" style="margin-top: 10px; margin-bottom: 10px">Transfer</V-btn>

    <v-card>
      <v-card-title>Tanks</v-card-title>
      <v-data-table
        :headers="regularHeaders"
        :items="regularTanks"
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
        <v-btn v-if="isCommander" color="error" @click="openSellTankDialog">Sell Tanks</v-btn>
      </v-card-actions>
    </v-card>

    <v-card>
      <v-card-title>Lore</v-card-title>
      <v-data-table
        :headers="tradHeaders"
        :items="tradTanks"
        item-key="name"
        dense
        class="team-table"
      >
        <template v-slot:[`item.available`]="{ item }">
          <span>
            <v-icon color="green" v-if="item.aval">mdi-check-circle</v-icon>
            <v-icon color="red" v-else>mdi-cancel</v-icon>
          </span>
        </template>

        <template v-slot:[`item.name`]="{ item }">
          <span>{{ item.name }}</span>
        </template>

        <template v-slot:[`item.tier`]="{ item }">
          <span>{{ item.tier || 'N/A' }}</span>
        </template>

        <template v-slot:[`item.quantity`]="{ item }">
          <span>{{ item.quantity }}</span>
        </template>
      </v-data-table>
    </v-card>

    <v-card>
      <v-card-title>Inventory</v-card-title>
      <v-data-table
        :headers="additionalInfoHeaders"
        :items="combinedItems"
        item-key="name"
        dense
        class="team-table"
        @click:row="handleKitClick"
      >
        <template v-slot:[`item.tier`]="{ item }">
          <span>{{ item.tier || 'N/A' }}</span>
        </template>
      </v-data-table>
    </v-card>

    <V-btn @click="goToManufacturers" style="margin-top: 10px; margin-bottom: 10px; margin-right: 10px">Manufacturer</V-btn>
    <V-btn v-if="(userStore.groups.some(i => i.name === 'commander') &&
             userStore.team === team.name) || userStore.groups.some(i => i.name === 'admin')" @click="showTransferDialog=true" style="margin-top: 10px; margin-bottom: 10px">Transfer</V-btn>

    <v-dialog v-model="showTransferDialog" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="headline">
            Money Transfer
          </span>
        </v-card-title>
        <v-card-text>
          <v-row>

            <v-col cols="12">
              <v-select
                v-model="selectedToTeam"
                :items="teams"
                item-text="name"
                item-value="id"
                label="Select Team to Transfer To"
                :rules="[value => !!value || 'Team is required']"
              ></v-select>
            </v-col>

            <v-col cols="6">
              <v-text-field
                v-model.number="preTaxAmount"
                label="Pre-Tax Amount"
                type="number"
                :rules="[value => value > 0 || 'Amount must be greater than 0']"
                @input="calculatePostTax"
              ></v-text-field>
            </v-col>

            <v-col cols="6">
              <v-text-field
                v-model.number="postTaxAmount"
                label="Post-Tax Amount"
                type="number"
                :rules="[value => value > 0 || 'Amount must be greater than 0']"
                @input="calculatePreTax"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions>
          <v-btn color="primary" @click="submitMoneyTransfer" :disabled="!selectedToTeam || !postTaxAmount || !preTaxAmount">
            Transfer
          </v-btn>
          <v-btn @click="showTransferDialog = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showMergeSplitDialog" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="headline">
            {{ selectedKit?.tier }} Upgrade Kit Conversion
          </span>
        </v-card-title>
        <v-card-text>
            <template v-if="previousKitTier">
              <strong>Current {{ previousKitTier }} Kits:</strong> {{ previousKitQuantity }}
            </template>
            <div>
              <strong>Current {{ selectedKit?.tier }} Kits:</strong> {{ selectedKit?.quantity }}
              <template v-if="selectedKit?.tier !== 'T3'">
                <br/>
                <strong>Current {{ nextKitTier }} Kits:</strong> {{ nextKitQuantity }}
              </template>
              <br/>
            </div>

          <v-row v-if="selectedKit?.tier !== 'T1'">
            <v-col cols="6">
              <v-text-field
                v-model.number="splittingInput"
                label="Number of Kits to Split"
                type="number"
                :rules="[value => value >= 0 && value <= selectedKit?.quantity || 'Invalid quantity']"
                @input="updateSplitInput"
              ></v-text-field>
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="splittingOutput"
                label="Number of Kits Received After Split"
                type="number"
                :rules="[value => value >= 0 || 'Invalid quantity']"
                @input="updateSplitOutput"
                step="2"
              ></v-text-field>
            </v-col>
          </v-row>

          <v-row v-if="selectedKit?.tier !== 'T3'">
            <v-col cols="6">
              <v-text-field
                v-model.number="conversionInput"
                label="Number of Kits to Merge"
                type="number"
                :rules="[value => value >= 0 && value <= selectedKit?.quantity || 'Invalid quantity']"
                @input="updateFromInput"
                step="2"
              ></v-text-field>
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="conversionOutput"
                label="Number of Kits Received After Merge"
                type="number"
                :rules="[value => value >= 0 || 'Invalid quantity']"
                @input="updateFromOutput"
              ></v-text-field>
            </v-col>
          </v-row>

        </v-card-text>
        <v-card-actions>
          <v-btn v-if="selectedKit?.tier !== 'T3'" color="primary" @click="submitMergeSplit('merge', selectedKit?.tier, conversionOutput)">Merge</v-btn>
          <v-btn v-if="selectedKit?.tier !== 'T1'" color="primary" @click="submitMergeSplit('split', selectedKit?.tier, splittingInput)">Split</v-btn>
          <v-btn @click="showMergeSplitDialog = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showTankDetailsDialog" @afterLeave="this.selectedUpgrade = null" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="headline">{{ selectedTank?.item.name }}</span>
        </v-card-title>
        <v-card-text>
          <div>
            <strong>Battle Rating:</strong> {{ selectedTank?.item.tier }}<br />
            <strong>Rank:</strong> {{ selectedTank?.item.rank }}<br />
            <strong>Sell Price:</strong> {{ selectedTank?.item.sellPrice }} <br/>
            <strong>Quantity:</strong> {{ selectedTank?.item.quantity }}
            <div style="display: flex; align-items: center; justify-items: center; height: 56px">
              <v-checkbox v-model="getAllUpgrades" style="height: 56px"></v-checkbox>
              <label>Show All Upgrades</label>
            </div>
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
          <v-btn v-if="isCommander && getAllUpgrades" color="primary" @click="upgradeTank">Upgrade</v-btn>
          <v-btn v-if="isCommander && !getAllUpgrades" color="primary" @click="upgradeTankDirect">Upgrade</v-btn>
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
              :items="regularTanks"
              item-key="name"
              dense
            >
              <template v-slot:[`item.quantityToSell`]="{ item }">
                <v-text-field
                  v-model.number="sellQuantities[item.name]"
                  :max="item.quantity"
                  type="number"
                  min="0"
                  :rules="[value => value >= 0 && value <= item.quantity || 'Invalid quantity']"
                  style="display: flex; align-items: center;"
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

    <v-dialog v-model="showSuccessDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Tanks Sold Successfully</v-card-title>
        <v-card-text>
          <p>Tanks Sold:</p>
          <ul>
            <li v-for="(tank, index) in soldTanks" :key="index">
              {{ tank.name }} (Quantity: {{ tank.quantity }})
            </li>
          </ul>
          <p>New Balance: {{ newBalance.toLocaleString() }}$</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showSuccessDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showTransferSuccessDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Money Transferred Successfully</v-card-title>
        <v-card-text>
          <p>{{ preTaxAmount }} Transferred to {{ selectedToTeam }}</p>
          <p>New Balance: {{ newBalance.toLocaleString() }}$</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="closeDialog()">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showUpgradeSuccessDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Tanks Upgraded Successfully</v-card-title>
        <v-card-text>
          <p>
              {{ upgradeDetailsForSuccessDialog.fromTank }} ->
              {{ upgradeDetailsForSuccessDialog.toTank }}
          </p>
          <p>New Balance: {{ newBalance.toLocaleString() }}$</p>
          <p>Updated Kits:</p>
          <ul>
            <li v-for="(kit, type) in newKits" :key="type">
              {{ type }} kits: {{ kit.quantity }}
            </li>
          </ul>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showUpgradeSuccessDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </v-container>
</template>

<script>
import {inject, toRef} from "vue";
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
      soldTanks: '',
      newBalance: 0,
      showSuccessDialog: false,
      showKitSuccessDialog: false,
      showUpgradeSuccessDialog: false,
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
        { title: 'Name', value: 'name' , sortable: true},
        { title: 'Tier', value: 'tier' , sortable: true},
        { title: 'Quantity', value: 'quantity', sortable: true }
      ],
      regularHeaders: [
        { title: 'Name', value: 'name' , sortable: true},
        { title: 'Battle Rating', value: 'tier', sortable: true },
        { title: 'Quantity', value: 'quantity', sortable: true }
      ],
      tradHeaders: [
        { title: '', value: 'available', width: '50px', sortable: true },
        { title: 'Name', value: 'name', sortable: true },
        { title: 'Battle Rating', value: 'tier', sortable: true },
        { title: 'Quantity', value: 'quantity', sortable: true },
      ],
      sellTankHeaders: [
        { title: 'Name', value: 'name', sortable: true },
        { title: 'Tier', value: 'tier', sortable: true },
        { title: 'Available Quantity', value: 'quantity', sortable: true },
        { title: 'Quantity to Sell', value: 'quantityToSell', sortable: true }
      ],
      userStore,
      showMergeSplitDialog: false,
      selectedKit: null,
      conversionInput: 0,
      conversionOutput: 0,
      splittingInput: 0,
      splittingOutput: 0,
      newKits: {},
      teams: null,
      showTransferDialog: false,
      showTransferSuccessDialog: false,
      selectedToTeam: null,
      preTaxAmount: 0,
      postTaxAmount: 0,
      getAllUpgrades: false,
      upgradeDetailsForSuccessDialog: null,
    };
  },
  computed: {
    nextKitTier() {
      if (!this.selectedKit) return '';
      return this.selectedKit.tier === 'T1' ? 'T2' : this.selectedKit.tier === 'T2' ? 'T3' : '';
    },
    nextKitQuantity() {
      const nextTier = this.nextKitTier;
      const nextKit = this.combinedItems.find(item => item.tier === nextTier);
      return nextKit ? nextKit.quantity : 0;
    },
    previousKitTier() {
      if (!this.selectedKit) return '';
      return this.selectedKit.tier === 'T2' ? 'T1' : this.selectedKit.tier === 'T3' ? 'T2' : '';
    },
    previousKitQuantity() {
      const prevTier = this.previousKitTier;
      const prevKit = this.combinedItems.find(item => item.tier === prevTier);
      return prevKit ? prevKit.quantity : 0;
    },
    regularTanks(){
      const tankCounts = this.team.tanks.reduce((acc, tank) => {
        if (!tank.is_trad) {
          acc[tank.tank.name] = acc[tank.tank.name] ? acc[tank.tank.name] + 1 : 1;
        }
        return acc;
      }, {});


      const uniqueTanks = new Set();

      const reg_tanks = this.team.tanks.reduce((acc, tank) => {
        const tankName = tank.tank.name;
        if (!uniqueTanks.has(tankName) && !tank.is_trad) {
          uniqueTanks.add(tankName);
          acc.push({
            name: tankName,
            rank: tank.tank.rank,
            tier: tank.tank.battle_rating.toFixed(1),
            quantity: tankCounts[tankName],
            sellPrice: tank.tank.price.toFixed(1) * 0.6,
          });
        }
        return acc;
      }, []);

      return reg_tanks.sort((a, b) => a.tier - b.tier);
    },
    tradTanks(){
      const tankCounts = this.team.tanks.reduce((acc, tank) => {
        if (tank.is_trad) {
          acc[tank.tank.name] = acc[tank.tank.name] ? acc[tank.tank.name] + 1 : 1;
        }
        return acc;
      }, {});

      const uniqueTanks = new Set();

      const trad_tanks = this.team.tanks.reduce((acc, tank) => {
        const tankName = tank.tank.name;
        if (!uniqueTanks.has(tankName) && tank.is_trad) {
          uniqueTanks.add(tankName);
          acc.push({
            name: tankName,
            rank: tank.tank.rank,
            tier: tank.tank.battle_rating.toFixed(1),
            quantity: tankCounts[tankName],
            aval: tank.available
          });
        }
        return acc;
      }, []);

      return trad_tanks.sort((a, b) => a.tier - b.tier);
    },
    combinedItems() {
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

      return [...tankBoxes, ...upgradeKits];
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

        for (const tier in requiredKits) {
          if (requiredKits[tier] > 0) {
            maxKits[tier] = Math.max(maxKits[tier] - requiredKits[tier], 0);
          }
        }
      }

      return maxKits;
    },
    totalCost() {
      const tier1Cost = (this.kitQuantities.T1 || 0) * (this.kitValues.T1 || 0);
      const tier2Cost = (this.kitQuantities.T2 || 0) * (this.kitValues.T2 || 0);
      const tier3Cost = (this.kitQuantities.T3 || 0) * (this.kitValues.T3 || 0);

      const totalKitsCost = tier1Cost + tier2Cost + tier3Cost;

      let new_cost = 0;

      if (this.selectedUpgradeDetails) {
        if (this.selectedUpgradeDetails.available_in_manufacturer) {
          new_cost = Math.max((this.selectedUpgradeDetails.manu_cost || 0) - totalKitsCost, 0);
        } else {
          new_cost = Math.max((this.selectedUpgradeDetails.total_cost || 0) - totalKitsCost, 0);
        }
      }
      return new_cost;
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
      } else {
        this.selectedUpgradeDetails = null;
      }
    },
    conversionInput(newVal) {
      this.conversionOutput = Math.floor(newVal / 2);
    },
    getAllUpgrades(newVal) {
      this.selectedUpgrade = null
      if (newVal){
        this.fetchPossibleUpgrades(this.selectedTank.item.name)
      }
      else {
        this.fetchPossibleDirectUpgrades(this.selectedTank.item.name)
      }
    }
  },
  methods: {
    async fetchTeams() {
      try {
        const response = await fetch('/api/league/teams/');
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const data = await response.json();
        const teamNames = data.map(team => team.name);
        this.teams = teamNames;
      } catch (error) {
        console.error('Error fetching teams:', error);
      }
    },
    async goToManufacturers() {
      const teamName = this.team.name;
      this.$router.push({name: 'Manufacturer', params: {TName: teamName}});
    },
    handleRowClick(event, row) {
      this.selectedTank = row;
      this.fetchPossibleDirectUpgrades(row.item.name);
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
        this.upgradeOptions = upgrades.map(upgrade => ({
          title: upgrade.to_tank,
          upgrade_path_id: upgrade.upgrade_path_id,
          to_tank: upgrade.to_tank,
          total_cost: upgrade.total_cost,
          required_kits: upgrade.required_kits,
          available_in_manufacturer: upgrade.available_in_manufacturer,
          manu_cost: upgrade.manu_cost,
          to_tank_br: upgrade.to_tank_br,
        })).sort((a, b) => a.to_tank_br - b.to_tank_br);
      } catch (error) {
        console.error("Error fetching possible upgrades:", error);
      }
    },
    async fetchPossibleDirectUpgrades(tankName) {
      try {
        const response = await fetch(`/api/league/transactions/view_upgrades/direct/`, {
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
        this.upgradeOptions = upgrades.map(upgrade => ({
          title: upgrade.to_tank,
          upgrade_path_id: upgrade.upgrade_path_id,
          to_tank: upgrade.to_tank,
          total_cost: upgrade.total_cost,
          required_kits: upgrade.required_kits,
          available_in_manufacturer: upgrade.available_in_manufacturer,
          manu_cost: upgrade.manu_cost,
          to_tank_br: upgrade.to_tank_br,
        })).sort((a, b) => a.to_tank_br - b.to_tank_br);
      } catch (error) {
        console.error("Error fetching possible upgrades:", error);
      }
    },
    async sellTank() {
      if (!this.selectedTank) return;

      const tanksToSell = [{name: this.selectedTank.item.name, quantity: 1}];

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

        const responseData = await response.json();
        this.soldTanks = responseData.sold_tanks;
        this.newBalance = responseData.new_balance;

        await this.fetchTeamDetails();
        this.showTankDetailsDialog = false;
        this.showSuccessDialog = true;
      } catch (error) {
        alert('Error during the sell operation:', error);
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

        const responseData = await response.json();
        this.newKits = responseData.new_kits;
        this.newBalance = responseData.new_balance;

        await this.fetchTeamDetails();
        this.upgradeDetailsForSuccessDialog = {
          fromTank: this.selectedTank?.item.name,
          toTank: this.upgradeOptions.find(u => u.upgrade_path_id === this.selectedUpgrade)?.to_tank,
          newBalance: this.newBalance,
          newKits: this.newKits,
        };
        this.showTankDetailsDialog = false;
        this.showUpgradeSuccessDialog = true;

      } catch (error) {
        alert('Error upgrading tank:', error);
      }
    },
    async upgradeTankDirect() {
      if (!this.selectedUpgrade) {
        return;
      }

      try {
        const upgradeDetails = this.upgradeOptions.find(u => u.to_tank === this.selectedUpgrade);
        const response = await fetch('/api/league/transactions/upgrade_tank/direct/', {
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

        const responseData = await response.json();
        this.newKits = responseData.new_kits;
        this.newBalance = responseData.new_balance;

        await this.fetchTeamDetails();
        this.upgradeDetailsForSuccessDialog = {
          fromTank: this.selectedTank?.item.name,
          toTank: this.upgradeOptions.find(u => u.upgrade_path_id === this.selectedUpgrade)?.to_tank,
          newBalance: this.newBalance,
          newKits: this.newKits,
        };
        this.showTankDetailsDialog = false;
        this.showUpgradeSuccessDialog = true;

      } catch (error) {
        alert('Error upgrading tank:', error);
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
        console.log(this.team)
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
          throw new Error('Error selling tanks');
        }

        const responseData = await response.json();
        this.soldTanks = responseData.sold_tanks;
        this.newBalance = responseData.new_balance;

        await this.fetchTeamDetails();
        this.showTankDetailsDialog = false;
        this.showSuccessDialog = true;
      } catch (error) {
        alert('Error during the sell operation:', error);
      }
    },
    getMaxKits(tier) {
      const tierKits = this.combinedItems.filter(item => item.tier === tier);
      const kitNumber = tierKits.reduce((total, item) => total + item.quantity, 0)
      return;
    },
    handleKitClick(event, row) {
      if (row.item.name === 'Upgrade Kit') {
        this.selectedKit = row.item;
        this.showMergeSplitDialog = true;
        this.conversionInput = 0;
        this.conversionOutput = 0;
      }
    },
    updateFromInput() {
      this.conversionOutput = Math.floor(this.conversionInput / 2);
    },
    updateFromOutput() {
      this.conversionInput = this.conversionOutput * 2;
    },
    updateSplitInput() {
      this.splittingOutput = this.splittingInput * 2;
    },
    updateSplitOutput() {
      this.splittingInput = Math.floor(this.splittingOutput / 2);
    },
    async submitMergeSplit(action, type, amount) {
      try {
        const response = await fetch('/api/league/transactions/merge_split_kit/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'authorization': getAuthToken()
          },
          body: JSON.stringify({
            team: this.team.name,
            action: action,
            kit_type: type,
            kit_amount: amount,
          })
        });

        if (!response.ok) {
          throw new Error('Error');
        }

        await this.fetchTeamDetails();

        this.showKitSuccessDialog = true
        this.splittingInput = 0;
        this.splittingOutput = 0;
        this.conversionInput = 0;
        this.conversionOutput = 0;
      } catch (error) {
        alert('Error during the merge operation:', error);
      }
    },
    calculatePostTax() {
      if (this.preTaxAmount === 0) {
        this.postTaxAmount = 0;
        return;
      }

      const amount = this.preTaxAmount;

      if (amount > 25000) {
        this.postTaxAmount = amount * 0.8;
      } else if (amount > 10000) {
        this.postTaxAmount = amount * 0.9;
      } else {
        this.postTaxAmount = amount * 0.95;
      }
      this.postTaxAmount = Math.floor(this.postTaxAmount)
    },
    calculatePreTax() {
      if (this.postTaxAmount === 0) {
        this.preTaxAmount = 0;
        return;
      }

      const taxedAmount = this.postTaxAmount;

      if (taxedAmount <= 10000 * 0.95) {
        this.preTaxAmount = taxedAmount / 0.95;
      } else if (taxedAmount <= 25000 * 0.9) {
        this.preTaxAmount = taxedAmount / 0.9;
      } else {
        this.preTaxAmount = taxedAmount / 0.8;
      }
      this.preTaxAmount = Math.floor(this.preTaxAmount)
    },
    async submitMoneyTransfer () {
      if (!this.selectedToTeam || !this.postTaxAmount || !this.preTaxAmount) {
        return;
      }

      try {
        const response = await fetch('/api/league/transactions/transfer/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'authorization': getAuthToken()
          },
          body: JSON.stringify({
            team: this.team.name,
            to_team: this.selectedToTeam,
            amount: this.preTaxAmount,
          }),
        });

        if (response.ok) {
          const responseData = await response.json();
          this.newBalance = responseData.new_balance;

          this.showTransferSuccessDialog = true;
          this.showTransferDialog = false;
        } else {
          alert(`Error: ${error.message}`);
        }
      } catch (error) {
        console.error('Error submitting transfer:', error);
        alert('There was an error processing your transfer.');
      }
    },
    closeDialog() {
      this.showTransferSuccessDialog = false
      this.preTaxAmount = 0
      this.postTaxAmount = 0
    }
  },
  created() {
    this.fetchTeamDetails();
    this.fetchTeams();
  },
};

</script>

<style scoped>
.team-table {
  cursor: pointer;
}

</style>