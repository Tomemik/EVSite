<template>
  <v-container>
    <v-card class="mb-6 elevation-2" shaped>
      <v-card-title class="d-flex justify-space-between align-center primary white--text py-4">
        <div class="d-flex align-center">
          <v-icon large color="white" class="mr-3">mdi-tank</v-icon>
          <div>
            <span class="text-h5 font-weight-bold">{{ team.name }}</span>
            <div class="subtitle-2 white--text opacity-70">
              Balance: {{ team.balance.toLocaleString() }}
            </div>
          </div>
        </div>
        <v-chip v-if="team.alliance_name" color="white" text-color="primary" class="font-weight-bold">
          <v-icon left small>mdi-shield-account</v-icon>
          {{ team.alliance_name }}
        </v-chip>
      </v-card-title>
    </v-card>

    <v-row class="mb-4 px-2">
      <v-btn
        @click="goToManufacturers"
        color="secondary"
        class="ml-1 mr-2"
        elevation="2"
      >
        <v-icon left>mdi-factory</v-icon> Manufacturer
      </v-btn>

      <v-btn
        v-if="(userStore.groups.some(i => i.name === 'commander') && userStore.team === team.name) || userStore.groups.some(i => i.name === 'admin')"
        @click="showTransferDialog=true"
        class="mr-2"
        color="success"
        elevation="2"
      >
        <v-icon left>mdi-bank-transfer</v-icon> Transfer Money
      </v-btn>

      <v-btn
        v-if="(userStore.groups.some(i => i.name === 'commander') && userStore.team === team.name) || userStore.groups.some(i => i.name === 'admin') && team.alliance_name"
        @click="showKitTransferDialog=true"
        color="success"
        elevation="2"
      >
        <v-icon left>mdi-bank-transfer</v-icon> Transfer Kits
      </v-btn>
    </v-row>

    <v-card class="mb-6 elevation-2">
      <v-card-title class="grey lighten-4 py-2">
        <v-icon left color="primary">mdi-tank-turret</v-icon>
        Active Tanks
      </v-card-title>
      <v-data-table
        :headers="regularHeaders"
        :items="regularTanks"
        item-key="name"
        dense
        class="team-table elevation-0"
        @click:row="handleRowClick"
      >
        <template v-slot:[`item.tier`]="{ item }">
          <v-chip x-small color="blue-grey lighten-4" class="font-weight-bold">
            {{ item.tier || 'N/A' }}
          </v-chip>
        </template>
        <template v-slot:[`item.display_name`]="{ item }">
          <span class="font-weight-medium">{{ item.display_name }}</span>
        </template>
      </v-data-table>
      <v-divider></v-divider>
      <v-card-actions v-if="isCommander" class="pa-3">
        <v-btn color="error" text small @click="openSellTankDialog">
          <v-icon left small>mdi-delete</v-icon> Bulk Sell
        </v-btn>
      </v-card-actions>
    </v-card>

    <v-row>
      <v-col cols="12" md="6">
        <v-card class="fill-height elevation-2">
          <v-card-title class="grey lighten-4 py-2 subtitle-1">
            <v-icon left small>mdi-book-open-page-variant</v-icon> Lore / Traditional
          </v-card-title>
          <v-data-table
            :headers="tradHeaders"
            :items="tradTanks"
            item-key="name"
            dense
            hide-default-footer
            class="team-table"
          >
            <template v-slot:[`item.available`]="{ item }">
              <v-icon small :color="item.aval ? 'success' : 'error'">
                {{ item.aval ? 'mdi-check-circle' : 'mdi-lock' }}
              </v-icon>
            </template>
          </v-data-table>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card class="fill-height elevation-2">
          <v-card-title class="grey lighten-4 py-2 subtitle-1">
            <v-icon left small>mdi-package-variant</v-icon> Inventory
          </v-card-title>
          <v-data-table
            :headers="additionalInfoHeaders"
            :items="combinedItems"
            item-key="name"
            dense
            hide-default-footer
            class="team-table"
            @click:row="handleInventoryClick"
          >
            <template v-slot:[`item.tier`]="{ item }">
              <v-chip x-small :color="item.tier.startsWith('T') ? 'amber lighten-4' : 'grey lighten-3'">
                {{ item.tier }}
              </v-chip>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="showTransferDialog" max-width="500px">
      <v-card>
        <v-card-title class="primary white--text">
          <v-icon left color="white">mdi-bank-transfer</v-icon> Money Transfer
        </v-card-title>
        <v-card-text class="pt-6">
          <v-autocomplete
            v-model="selectedToTeam"
            :items="teams"
            label="Recipient Team"
            outlined
            dense
            prepend-inner-icon="mdi-account-arrow-right"
          ></v-autocomplete>

          <v-row>
            <v-col cols="6">
              <v-text-field
                v-model.number="preTaxAmount"
                label="Amount (Pre-Tax)"
                type="number"
                outlined
                dense
                @input="calculatePostTax"
                color="primary"
              ></v-text-field>
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="postTaxAmount"
                label="Receiver Gets"
                type="number"
                outlined
                dense
                @input="calculatePreTax"
                color="success"
                hint="Tax deducted automatically"
                persistent-hint
              ></v-text-field>
            </v-col>
          </v-row>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text color="grey darken-1" @click="showTransferDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="submitMoneyTransfer" :disabled="!selectedToTeam || !postTaxAmount">
            Confirm Transfer
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showMergeSplitDialog" max-width="650px">
      <v-card>
        <v-card-title class="amber lighten-5 d-flex justify-space-between">
          <span class="headline brown--text">Inventory Management</span>
          <v-chip color="amber" text-color="brown" class="font-weight-bold">
            {{ selectedKit?.tier }} Kits
          </v-chip>
        </v-card-title>

        <v-card-text class="pt-4">
          <v-row class="text-center mb-4">
            <v-col v-if="previousKitTier" cols="4">
              <div class="caption grey--text">Lower Tier ({{ previousKitTier }})</div>
              <div class="text-h6">{{ previousKitQuantity }}</div>
            </v-col>
            <v-col cols="4" class="amber lighten-5 rounded">
              <div class="caption brown--text font-weight-bold">Current ({{ selectedKit?.tier }})</div>
              <div class="text-h5 brown--text font-weight-bold">{{ selectedKit?.quantity }}</div>
            </v-col>
            <v-col v-if="nextKitTier" cols="4">
              <div class="caption grey--text">Higher Tier ({{ nextKitTier }})</div>
              <div class="text-h6">{{ nextKitQuantity }}</div>
            </v-col>
          </v-row>

          <v-divider class="mb-4"></v-divider>

          <v-row>
            <v-col cols="6" v-if="selectedKit?.tier !== 'T1'" class="pr-4 border-right">
              <div class="subtitle-2 mb-2 d-flex align-center">
                <v-icon small class="mr-1">mdi-call-split</v-icon> Split Down
              </div>
              <div class="d-flex align-center">
                <v-text-field
                  v-model.number="splittingInput"
                  label="Convert"
                  outlined dense type="number"
                  hide-details
                  class="mr-2"
                ></v-text-field>
                <v-icon color="grey">mdi-arrow-right</v-icon>
                <v-text-field
                  v-model.number="splittingOutput"
                  label="Result"
                  outlined dense readonly filled
                  hide-details
                  class="ml-2"
                ></v-text-field>
              </div>
              <v-btn
                block small color="primary" class="mt-3"
                @click="submitMergeSplit('split', selectedKit?.tier, splittingInput)"
                :disabled="splittingInput <= 0"
              >Split</v-btn>
            </v-col>

            <v-col cols="6" v-if="selectedKit?.tier !== 'T3'" class="pl-4">
              <div class="subtitle-2 mb-2 d-flex align-center">
                <v-icon small class="mr-1">mdi-call-merge</v-icon> Merge Up
              </div>
              <div class="d-flex align-center">
                <v-text-field
                  v-model.number="conversionInput"
                  label="Convert"
                  outlined dense type="number"
                  hide-details
                  class="mr-2"
                ></v-text-field>
                <v-icon color="grey">mdi-arrow-right</v-icon>
                <v-text-field
                  v-model.number="conversionOutput"
                  label="Result"
                  outlined dense readonly filled
                  hide-details
                  class="ml-2"
                ></v-text-field>
              </div>
              <v-btn
                block small color="secondary" class="mt-3"
                @click="submitMergeSplit('merge', selectedKit?.tier, conversionOutput)"
                :disabled="conversionInput <= 0"
              >Merge</v-btn>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions class="grey lighten-4">
          <v-btn
            v-if="selectedKit?.tier === 'T1' && team.alliance_name"
            color="orange darken-3"
            text
            @click="openKitTransferDialog"
          >
            <v-icon left>mdi-account-arrow-right</v-icon> Send to Alliance
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn text @click="showMergeSplitDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showTankDetailsDialog" @afterLeave="this.selectedUpgrade = null" max-width="700px">
      <v-card>
        <v-card-title class="text-h4 font-weight-bold ml-2 mb-1">
          {{ selectedTank?.item.name }}
        </v-card-title>

        <v-card-text class="pt-4">
          <v-row class="mb-2">
            <v-col cols="4">
              <v-sheet rounded color="grey lighten-4" class="pa-2 text-center">
                <div class="caption grey--text">Battle Rating</div>
                <div class="font-weight-bold">{{ selectedTank?.item.tier }}</div>
              </v-sheet>
            </v-col>
            <v-col cols="4">
              <v-sheet rounded color="grey lighten-4" class="pa-2 text-center">
                <div class="caption grey--text">Rank</div>
                <div class="font-weight-bold">{{ selectedTank?.item.rank }}</div>
              </v-sheet>
            </v-col>
            <v-col cols="4">
              <v-sheet rounded color="grey lighten-4" class="pa-2 text-center">
                <div class="caption grey--text">Sell Value</div>
                <div class="font-weight-bold success--text">{{ selectedTank?.item.sellPrice }}</div>
              </v-sheet>
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>

          <div class="d-flex align-center justify-space-between mb-2">
            <h3 class="text-h6">Upgrade Configuration</h3>
            <v-switch
              v-model="getAllUpgrades"
              label="All Upgrades"
              dense hide-details
              class="mt-0"
              color="primary"
            ></v-switch>
          </div>

          <v-autocomplete
            v-model="selectedUpgrade"
            :items="upgradeOptions"
            item-text="to_tank"
            item-value="upgrade_path_id"
            label="Select Target Tank"
            outlined
            dense
            prepend-inner-icon="mdi-arrow-up-bold-circle"
          >
          </v-autocomplete>

          <div class="caption mb-1 ml-1 font-weight-bold grey--text text--darken-1">Apply EXTRA Upgrade Kits</div>
          <v-row dense>
            <v-col cols="4">
              <v-text-field
                v-model.number="kitQuantities.T1"
                label="Tier 1"
                type="number"
                outlined dense
                :max="maxKits.T1"
                min="0"
                color="brown"
              ></v-text-field>
            </v-col>
            <v-col cols="4">
              <v-text-field
                v-model.number="kitQuantities.T2"
                label="Tier 2"
                type="number"
                outlined dense
                :max="maxKits.T2"
                min="0"
                color="blue-grey"
              ></v-text-field>
            </v-col>
            <v-col cols="4">
              <v-text-field
                v-model.number="kitQuantities.T3"
                label="Tier 3"
                type="number"
                outlined dense
                :max="maxKits.T3"
                min="0"
                color="amber"
              ></v-text-field>
            </v-col>
          </v-row>

          <v-alert
            v-if="selectedUpgradeDetails"
            dense
            border="left"
            colored-border
            :color="selectedUpgradeDetails.available_in_manufacturer ? 'success' : 'info'"
            elevation="1"
            class="mt-2"
          >
            <div class="d-flex justify-space-between align-center">
              <div>
                <div class="caption grey--text">Total Cost</div>
                <div class="text-h6 font-weight-bold">
                  {{ totalCost.toLocaleString() }}
                </div>
              </div>
              <div class="text-right">
                <div v-if="selectedUpgradeDetails.available_in_manufacturer" class="success--text font-weight-bold">
                  <v-icon color="success" small>mdi-check</v-icon> Manufacturer Available
                </div>
                <div v-else>
                  <div class="caption grey--text">Required Kits</div>
                  <div class="font-weight-medium">
                    {{
                      Object.entries(selectedUpgradeDetails.required_kits).filter(([k,v]) => v > 0).length
                        ? Object.entries(selectedUpgradeDetails.required_kits)
                            .map(([key, value]) => `${value}x ${key}`)
                            .join(', ')
                        : 'None'
                    }}
                  </div>
                </div>
              </div>
            </div>
          </v-alert>

        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4">
          <v-btn v-if="isCommander" color="error" text @click="sellTank">
            <v-icon left>mdi-cash-minus</v-icon> Sell
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn text @click="showTankDetailsDialog = false">Cancel</v-btn>

          <v-btn
            v-if="isCommander"
            color="primary"
            elevation="2"
            @click="getAllUpgrades ? upgradeTank() : upgradeTankDirect()"
            :disabled="!selectedUpgrade"
          >
            <v-icon left>mdi-wrench</v-icon> Confirm Upgrade
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showSellTankDialog" max-width="600px">
      <v-card>
        <v-card-title class="error white--text">
          <v-icon left color="white">mdi-delete-alert</v-icon> Sell Tanks
        </v-card-title>
        <v-card-text class="pt-4">
          <v-data-table
            :headers="sellTankHeaders"
            :items="filteredTanks"
            item-key="id"
            dense
            class="elevation-0"
          >
            <template v-slot:[`item.quantityToSell`]="{ item }">
              <v-text-field
                v-model.number="sellQuantities[item.name]"
                :max="item.quantity"
                type="number"
                min="0"
                dense outlined
                hide-details
                class="mt-1 mb-1"
                style="max-width: 100px"
              ></v-text-field>
            </template>
          </v-data-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showSellTankDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="sellTanks">Confirm Sale</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showKitTransferDialog" max-width="400px">
      <v-card>
        <v-card-title class="orange darken-3 white--text">
          <v-icon left color="white">mdi-gift</v-icon> Alliance Transfer
        </v-card-title>
        <v-card-text class="pt-4">
          <v-alert type="info" dense text>
            Sending to <strong>{{ team.alliance_name }}</strong> members.<br>
            Max 2 T1 kits per week.
          </v-alert>
          <v-select
            v-model="selectedKitTransferTeam"
            :items="allianceTeammates"
            label="Recipient"
            outlined dense
          ></v-select>
          <v-text-field
            v-model.number="kitTransferAmount"
            label="Quantity"
            type="number"
            min="1" max="2"
            outlined dense
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showKitTransferDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="submitKitTransfer" :disabled="!selectedKitTransferTeam">Send</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showBoxDialog" max-width="400px">
      <v-card class="text-center pa-4">
        <v-icon size="64" color="primary">mdi-package-variant-closed</v-icon>
        <div class="text-h5 font-weight-bold mt-2">Open Loot Box?</div>
        <div class="subtitle-1 mt-1">{{ selectedBox?.name }} (Tier {{ selectedBox?.tier }})</div>
        <v-card-actions class="justify-center mt-4">
          <v-btn text @click="showBoxDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="openBox" elevation="2">Open Now</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showSuccessDialog" max-width="400">
      <v-card>
        <v-card-title class="success white--text">Success</v-card-title>
        <v-card-text class="pt-4">
          <div v-for="(tank, index) in soldTanks" :key="index">
            Sold: {{ tank.quantity }} x {{ tank.name }}
          </div>
          <div class="mt-2 font-weight-bold">New Balance: {{ newBalance.toLocaleString() }}</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="showSuccessDialog = false">OK</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showUpgradeSuccessDialog" max-width="400">
      <v-card>
        <v-card-title class="success white--text">Upgrade Complete</v-card-title>
        <v-card-text class="pt-4 text-center">
          <v-icon size="48" color="success">mdi-arrow-up-bold-circle-outline</v-icon>
          <div class="title mt-2">
            {{ upgradeDetailsForSuccessDialog?.fromTank }} <br>
            <v-icon>mdi-arrow-down</v-icon> <br>
            {{ upgradeDetailsForSuccessDialog?.toTank }}
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="showUpgradeSuccessDialog = false">OK</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showTransferSuccessDialog" max-width="400">
      <v-card>
        <v-card-title class="success white--text">Transfer Complete</v-card-title>
        <v-card-text class="pt-4">
          Sent {{ preTaxAmount?.toLocaleString() }} to {{ selectedToTeam }}.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="closeDialog()">OK</v-btn>
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
        upgrade_kits: {},
        alliance_name: null,
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
      kitQuantities: { T1: 0, T2: 0, T3: 0 },
      kitValues: { T1: 25000, T2: 50000, T3: 100000 },
      baseCost: 0,
      additionalInfoHeaders: [
        { title: 'Name', value: 'name' , sortable: true},
        { title: 'Tier', value: 'tier' , sortable: true},
        { title: 'Quantity', value: 'quantity', sortable: true }
      ],
      regularHeaders: [
        { title: 'Name', value: 'display_name' , sortable: true},
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
        { title: 'Name', value: 'display_name', sortable: true },
        { title: 'Tier', value: 'tier', sortable: true },
        { title: 'Available Quantity', value: 'quantity', sortable: true },
        { title: 'Quantity to Sell', value: 'quantityToSell', sortable: true }
      ],
      userStore,
      showMergeSplitDialog: false,
      selectedKit: null,
      selectedBox: null,
      showBoxDialog: false,
      conversionInput: 0,
      conversionOutput: 0,
      splittingInput: 0,
      splittingOutput: 0,
      newKits: {},
      teams: [],
      showTransferDialog: false,
      showTransferSuccessDialog: false,
      selectedToTeam: null,
      preTaxAmount: 0,
      postTaxAmount: 0,
      getAllUpgrades: false,
      upgradeDetailsForSuccessDialog: null,

      // NEW PROPS FOR KIT TRANSFER
      showKitTransferDialog: false,
      selectedKitTransferTeam: null,
      kitTransferAmount: 1,
    };
  },
  computed: {
    // ... [Existing Computeds] ...
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
    regularTanks() {
      const tankCounts = this.team.tanks.reduce((acc, tank) => {
        const displayName = tank.from_auctions ? `{tank.tank.name}*` : tank.tank.name;
        if (!tank.is_trad) {
          acc[displayName] = acc[displayName] ? acc[displayName] + 1 : 1;
        }
        return acc;
      }, {});

      const uniqueTanks = new Set();

      const reg_tanks = this.team.tanks.reduce((acc, tank) => {
        if (tank.is_trad) return acc;

        const displayName = tank.from_auctions ? `{tank.tank.name}*` : tank.tank.name;
        const actualName = tank.tank.name;

        if (!uniqueTanks.has(displayName)) {
          uniqueTanks.add(displayName);
          acc.push({
            id: tank.id,
            display_name: displayName,
            name: actualName,
            rank: tank.tank.rank,
            tier: tank.tank.battle_rating.toFixed(1),
            quantity: tankCounts[displayName],
            sellPrice: (tank.value !== 0 ? tank.value * 0.6 : tank.tank.price * 0.6).toFixed(1),
          });
        }
        return acc;
      }, []);

      return reg_tanks.sort((a, b) => a.tier - b.tier);
    },
    tradTanks() {
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
        tier: box.box_tier,
        quantity: 1,
        id: box.id,
      }));

      const upgradeKits = Object.keys(this.team.upgrade_kits).map(key => ({
        name: `Upgrade Kit`,
        tier: key,
        quantity: this.team.upgrade_kits[key].quantity
      }));

      return [...tankBoxes, ...upgradeKits];
    },
    filteredTanks() {
      return this.regularTanks.filter(tank => tank.name === tank.display_name);
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
    allianceTeammates() {
      if (!this.team.alliance_name || this.allTeams.length === 0) return [];

      return this.allTeams
        .filter(t =>
          t.alliance_name &&
          t.alliance_name === this.team.alliance_name &&
          t.name !== this.team.name
        )
        .map(t => t.name);
    }
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
        this.fetchPossibleUpgrades(this.selectedTank.item)
      }
      else {
        this.fetchPossibleDirectUpgrades(this.selectedTank.item)
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
        this.allTeams = data;
        const teamNames = data.map(team => team.name);
        this.teams = teamNames;
      } catch (error) {
        console.error('Error fetching teams:', error);
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
    async goToManufacturers() {
      const teamName = this.team.name;
      this.$router.push({name: 'Manufacturer', params: {TName: teamName}});
    },
    handleRowClick(event, row) {
      this.selectedTank = row;
      this.fetchPossibleDirectUpgrades(this.selectedTank.item);
      this.showTankDetailsDialog = true;
      this.kitQuantities.T1 = 0;
      this.kitQuantities.T2 = 0;
      this.kitQuantities.T3 = 0;
    },
    async fetchPossibleUpgrades(tank) {
      try {
        const response = await fetch(`/api/league/transactions/view_upgrades/`, {
          method: 'GET',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'team': this.team.name,
            'tank': tank.id,
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
    async fetchPossibleDirectUpgrades(tank) {
      console.log(tank.id)
      try {
        const response = await fetch(`/api/league/transactions/view_upgrades/direct/`, {
          method: 'GET',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'team': this.team.name,
            'tank': tank.id,
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
      const tanksToSell = [this.selectedTank.item.id];
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
        if (!response.ok) { const res = await response.json(); alert(`Error Selling tank: ${res.error}`); }
        const responseData = await response.json();
        this.soldTanks = responseData.sold_tanks.map(tankName => ({
          name: tankName,
          quantity: 1
        }));
        this.newBalance = responseData.new_balance;
        await this.fetchTeamDetails();
        this.showTankDetailsDialog = false;
        this.showSuccessDialog = true;
      } catch (error) {
      }
    },
    async upgradeTank() {
      if (!this.selectedUpgrade) { return; }
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
            from_tank: this.selectedTank.item.id,
            to_tank: upgradeDetails.to_tank,
            kits: this.kitQuantities
          })
        });
        if (!response.ok) { const res = await response.json(); alert(`Error upgrading tank: ${res}`); }
        const responseData = await response.json();
        this.newKits = responseData.new_kits;
        this.newBalance = responseData.new_balance;
        await this.fetchTeamDetails();
        this.upgradeDetailsForSuccessDialog = {
          fromTank: this.selectedTank?.item.name,
          toTank: this.selectedUpgradeDetails?.to_tank,
          newBalance: this.newBalance,
          newKits: this.newKits,
        };
        this.showTankDetailsDialog = false;
        this.showUpgradeSuccessDialog = true;
      } catch (error) { console.error('Error upgrading tank:', error); }
    },
    async upgradeTankDirect() {
      if (!this.selectedUpgrade) { return; }
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
            from_tank: this.selectedTank.item.id,
            to_tank: upgradeDetails.to_tank,
            kits: this.kitQuantities
          })
        });
        if (!response.ok) { const res = await response.json(); alert(`Error upgrading tank: ${res}`); }
        const responseData = await response.json();
        this.newKits = responseData.new_kits;
        this.newBalance = responseData.new_balance;
        await this.fetchTeamDetails();
        this.upgradeDetailsForSuccessDialog = {
          fromTank: this.selectedTank?.item.name,
          toTank: this.selectedUpgradeDetails?.to_tank,
          newBalance: this.newBalance,
          newKits: this.newKits,
        };
        this.showTankDetailsDialog = false;
        this.showUpgradeSuccessDialog = true;
      } catch (error) { console.error('Error upgrading tank:', error); }
    },
    openSellTankDialog() { this.showSellTankDialog = true; },
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
        if (!response.ok) { const res = await response.json(); alert(`Error Selling tank: ${res.error}`); }
        const responseData = await response.json();
        this.soldTanks = responseData.sold_tanks;
        this.newBalance = responseData.new_balance;
        await this.fetchTeamDetails();
        this.showTankDetailsDialog = false;
        this.showSuccessDialog = true;
      } catch (error) {}
    },
    getMaxKits(tier) {
      const tierKits = this.combinedItems.filter(item => item.tier === tier);
      const kitNumber = tierKits.reduce((total, item) => total + item.quantity, 0)
      return;
    },
    // ... [Inventory Logic] ...
    handleInventoryClick(event, row) {
      if (row.item.name === 'Upgrade Kit') {
        this.selectedKit = row.item;
        this.showMergeSplitDialog = true;
        this.conversionInput = 0;
        this.conversionOutput = 0;
      } else {
        this.selectedBox = row.item;
        this.showBoxDialog = true;
      }
    },
    updateFromInput() { this.conversionOutput = Math.floor(this.conversionInput / 2); },
    updateFromOutput() { this.conversionInput = this.conversionOutput * 2; },
    updateSplitInput() { this.splittingOutput = this.splittingInput * 2; },
    updateSplitOutput() { this.splittingInput = Math.floor(this.splittingOutput / 2); },
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
        if (!response.ok) { const res = await response.json(); alert(`Error: ${res.error}`); }
        await this.fetchTeamDetails();
        this.showKitSuccessDialog = true
        this.splittingInput = 0;
        this.splittingOutput = 0;
        this.conversionInput = 0;
        this.conversionOutput = 0;
      } catch (error) {}
    },
    // ... [Transfer Money Logic] ...
    calculatePostTax() {
      if (this.preTaxAmount === 0) { this.postTaxAmount = 0; return; }
      const amount = this.preTaxAmount;
      if (amount > 25000) { this.postTaxAmount = amount * 0.8; }
      else if (amount > 10000) { this.postTaxAmount = amount * 0.9; }
      else { this.postTaxAmount = amount * 0.95; }
      this.postTaxAmount = Math.floor(this.postTaxAmount)
    },
    calculatePreTax() {
      if (this.postTaxAmount === 0) { this.preTaxAmount = 0; return; }
      const taxedAmount = this.postTaxAmount;
      if (taxedAmount <= 10000 * 0.95) { this.preTaxAmount = taxedAmount / 0.95; }
      else if (taxedAmount <= 25000 * 0.9) { this.preTaxAmount = taxedAmount / 0.9; }
      else { this.preTaxAmount = taxedAmount / 0.8; }
      this.preTaxAmount = Math.floor(this.preTaxAmount)
    },
    async submitMoneyTransfer () {
      if (!this.selectedToTeam || !this.postTaxAmount || !this.preTaxAmount) { return; }
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
        } else { alert(`Error: ${error.message}`); }
      } catch (error) { console.error('Error submitting transfer:', error); alert('There was an error processing your transfer.'); }
    },
    async openBox () {
      try {
        const response = await fetch('/api/league/transactions/open_box/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'Authorization': getAuthToken(),
          },
          body: JSON.stringify({
            team: this.team.name,
            box_id: this.selectedBox.id,
          }),
        });
        const data = await response.json();
        this.showBoxDialog = false
        console.log(response)
        if (response.ok) {
          await this.fetchTeamDetails();
          alert(`Box opened: ${data}`);
        } else { alert('Failed to open box.'); }
      } catch (error) { console.error('Error opening box:', error); }
    },
    closeDialog() {
      this.showTransferSuccessDialog = false
      this.preTaxAmount = 0
      this.postTaxAmount = 0
    },

    openKitTransferDialog() {
      this.showMergeSplitDialog = false; // Close parent dialog
      this.showKitTransferDialog = true; // Open transfer dialog
      this.selectedKitTransferTeam = null;
      this.kitTransferAmount = 1;
    },
    async submitKitTransfer() {
      if (!this.selectedKitTransferTeam || this.kitTransferAmount < 1) return;

      try {
        const response = await fetch('/api/league/transactions/transfer-kit/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'Authorization': getAuthToken(),
          },
          body: JSON.stringify({
            team: this.team.name,
            target_team: this.selectedKitTransferTeam,
            amount: this.kitTransferAmount,
          }),
        });

        const data = await response.json();

        if (response.ok) {
          alert(`Successfully sent ${this.kitTransferAmount} kit(s) to ${this.selectedKitTransferTeam}`);
          await this.fetchTeamDetails(); // Refresh inventory
          this.showKitTransferDialog = false;
        } else {
          alert(`Failed: ${data.error || 'Unknown error'}`);
        }
      } catch (error) {
        console.error('Error transferring kit:', error);
        alert('API Error during kit transfer');
      }
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
.team-table >>> .v-data-table__wrapper {
  overflow-x: hidden;
}
.v-alert__content {
  width: 100%;
}
.border-right {
  border-right: 1px solid #e0e0e0;
}
</style>