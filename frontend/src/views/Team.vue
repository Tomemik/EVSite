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
      >
        <template v-slot:[`item.tier`]="{ item }">
          <span>{{ item.tier || 'N/A' }}</span>
        </template>
      </v-data-table>

      <v-card-actions>
        <v-btn
          color="error"
          @click="openSellTankDialog"
        >
          Sell Tanks
        </v-btn>
      </v-card-actions>
    </v-card>

    <v-row class="mt-4 ml-0 mr-1" justify="end">
      <v-spacer></v-spacer>
      <v-btn
        color="primary"
        @click="goToManufacturers"
      >
        Manufacturer
      </v-btn>
    </v-row>

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
import {inject} from "vue";
import Manufacturer from "./Manufacturer.vue";

export default {
  components: {Manufacturer},
  data() {
    const $cookies = inject("$cookies");
    const csrfToken = $cookies.get('csrftoken');
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
      sellQuantities: {},
      sellTankHeaders: [
        { text: 'Name', value: 'name' },
        { text: 'Tier', value: 'tier' },
        { text: 'Available Quantity', value: 'quantity' },
        { text: 'Quantity to Sell', value: 'quantityToSell' }
      ]
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
    }
  },
  methods: {
    goToManufacturers() {
      const teamName = this.team.name;
      this.$router.push({name: 'Manufacturer', params: {TName: teamName}});
    },
    openSellTankDialog() {
      this.sellQuantities = {};
      this.filteredTanks.forEach(tank => {
        this.sellQuantities[tank.name] = 0;
      });
      this.showSellTankDialog = true;
    },
    async sellTanks() {
      const tanksToSell = this.filteredTanks
        .filter(item => this.sellQuantities[item.name] > 0)
        .map(item => ({
          name: item.name,
          quantity: this.sellQuantities[item.name]
        }));

      if (tanksToSell.length === 0) {
        return;
      }

      try {
        const response = await fetch('/api/league/transactions/sell_tanks/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json'
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
    }
  },
  created() {
    this.fetchTeamDetails();
  }
};
</script>

<style>
.team-table .v-data-table__wrapper {
  border-collapse: collapse;
}

.team-table th, .team-table td {
  border: 1px solid #ddd;
  padding: 8px;
}

.team-table th {
  text-align: center;
}

.team-table td {
  text-align: center;
}
</style>