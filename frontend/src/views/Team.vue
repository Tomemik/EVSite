<template>
  <v-container>
    <v-card class="mb-4">
      <v-card-title>
        <span class="headline">{{ team.name }}</span>
      </v-card-title>
      <v-card-subtitle>Balance: {{ team.balance.toLocaleString() }}</v-card-subtitle>
    </v-card>

    <v-row v-for="manufacturer in team.manufacturers" :key="manufacturer.id" class="mb-8">
      <v-col cols="12">
        <v-card>
          <v-card-title>{{ manufacturer.name }}</v-card-title>
          <v-card-text>
            <v-data-table
              :headers="manufacturerHeaders"
              :items="manufacturer.tanks"
              item-key="id"
              show-select
              v-model="selectedItems[manufacturer.id]"
              dense
              class="team-table"
            >
              <template v-slot:[`item.battle_rating`]="{ item }">
                <span>{{ item.battle_rating.toFixed(1) }}</span>
              </template>
            </v-data-table>
          </v-card-text>
          <v-card-actions>
            <v-btn
              @click="removeSelectedTanks(manufacturer.id)"
              color="error"
              :disabled="!(selectedItems[manufacturer.id] && selectedItems[manufacturer.id].length > 0)"
            >
              Remove Selected Tanks
            </v-btn>
            <v-btn
              @click="openAddTankDialog(manufacturer.id)"
              color="primary"
            >
              Add Tank
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-card>
      <v-card-title>Inventory</v-card-title>
      <v-data-table
        :headers="additionalInfoHeaders"
        :items="combinedItems"
        item-key="id"
        dense
        class="team-table"
      >
        <template v-slot:[`item.tier`]="{ item }">
          <span>{{ item.tier || 'N/A' }}</span>
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="showAddTankDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="headline">Add New Tank</span>
        </v-card-title>
        <v-card-text>
          <v-form ref="addTankForm">
            <v-text-field
              v-model="newTankName"
              label="Tank Name"
              required
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="addTank">Add Tank</v-btn>
          <v-btn @click="showAddTankDialog = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
import {inject} from "vue";

export default {
  data() {
    const $cookies = inject("$cookies");
    const csrfToken = $cookies.get('csrftoken');
    return {
      csrfToken,
      team: {
        name: '',
        balance: 0,
        manufacturers: [],
        tanks: [],
        tank_boxes: [],
        upgrade_kits: {}
      },
      selectedItems: {},
      showAddTankDialog: false,
      newTankName: '',
      selectedManufacturer: null,
      manufacturerHeaders: [
        { text: 'Name', value: 'name' },
        { text: 'Battle Rating', value: 'battle_rating' },
        { text: 'Price', value: 'price' },
        { text: 'Rank', value: 'rank' },
        { text: 'Type', value: 'type' }
      ],
      additionalInfoHeaders: [
        { text: 'Name', value: 'name' },
        { text: 'Battle Rating / Tier', value: 'tier' },
        { text: 'Quantity', value: 'quantity' }
      ]
    };
  },
  computed: {
    combinedItems() {
      const tankCounts = this.team.tanks.reduce((acc, tank) => {
        acc[tank.id] = acc[tank.id] ? acc[tank.id] + 1 : 1;
        return acc;
      }, {});

      const tanks = this.team.tanks.map(tank => ({
        id: tank.id,
        name: tank.name,
        tier: tank.battle_rating.toFixed(1),
        quantity: tankCounts[tank.id]
      }));

      const tankBoxes = this.team.tank_boxes.map(box => ({
        id: box.box_id,
        name: box.box_name,
        tier: '', // No battle rating for boxes
        quantity: box.amount
      }));

      const upgradeKits = Object.keys(this.team.upgrade_kits).map(key => ({
        id: key,
        name: `Upgrade Kit `,
        tier: key,
        quantity: this.team.upgrade_kits[key].quantity
      }));

      return [...tanks, ...tankBoxes, ...upgradeKits];
    }
  },
  methods: {
    async fetchTeamDetails() {
      const teamName = this.$route.params.TName;
      try {
        const response = await fetch(`/api/league/teams/${teamName}/`);
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        this.team = await response.json();
        this.selectedItems = this.team.manufacturers.reduce((acc, manufacturer) => {
          acc[manufacturer.id] = [];
          return acc;
        }, {});
      } catch (error) {
        console.error('Error fetching team details:', error);
      }
    },
    async removeSelectedTanks(manufacturerId) {
      if (!this.selectedItems[manufacturerId] || this.selectedItems[manufacturerId].length === 0) {
          return;
        }
        try {
          const tankNames = this.team.manufacturers
            .find(m => m.id === manufacturerId)
            ?.tanks.filter(t => this.selectedItems[manufacturerId].includes(t.id))
            .map(t => t.name) || [];

          const response = await fetch(`/api/league/manufacturers/${manufacturerId}/`, {
            method: 'PATCH',
            headers: {
              'X-CSRFToken': this.csrfToken,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({"remove_tank_names": tankNames}),
          });

          if (!response.ok) {
            throw new Error('Network response was not ok');
          }

          this.selectedItems[manufacturerId] = [];
          await this.fetchTeamDetails();
        } catch (error) {
          console.error('There was a problem with the fetch operation:', error);
        }
    },
    openAddTankDialog(manufacturerId) {
      this.selectedManufacturer = manufacturerId;
      this.showAddTankDialog = true;
    },
    async addTank() {
      if (!this.selectedManufacturer || this.newTankName.trim() === '') {
        return;
      }

      try {
        const response = await fetch(`/api/league/manufacturers/${this.selectedManufacturer}/`, {
          method: 'PATCH',
          headers: {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({"add_tank_names": [this.newTankName]}),
        });

        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        this.newTankName = '';
        this.showAddTankDialog = false;
        await this.fetchTeamDetails();
      } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
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