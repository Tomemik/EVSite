<template>
  <v-container>
    <v-row class="mb-4">
      <v-col>
        <h1 class="text-h4 font-weight-bold">Alliances</h1>
      </v-col>
      <v-col class="text-right">
        <v-btn
          icon="mdi-refresh"
          variant="text"
          @click="fetchAlliances"
          :loading="loading"
          color="primary"
        />
      </v-col>
    </v-row>

    <div v-if="loading" class="d-flex justify-center mt-10">
      <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
    </div>

    <div v-else-if="!alliances.length" class="text-center text-grey mt-10">
      <v-icon size="64" color="grey-lighten-2">mdi-shield-off-outline</v-icon>
      <div class="mt-2 text-h6">No alliances formed yet.</div>
    </div>

    <v-row v-else>
      <v-col
        v-for="alliance in alliances"
        :key="alliance.id"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card class="fill-height alliance-card" elevation="2">
          <v-sheet :color="alliance.color || 'primary'" height="6" width="100%"></v-sheet>

          <v-card-title class="d-flex align-center justify-space-between pt-4">
            <span class="text-h5 font-weight-bold">{{ alliance.name }}</span>
            <v-chip size="small" variant="tonal" color="grey-darken-1">
              {{ alliance.teams.length }} Members
            </v-chip>
          </v-card-title>

          <v-card-text>
            <v-divider class="mb-3"></v-divider>

            <div class="d-flex flex-wrap">
              <v-chip
                v-for="team in alliance.teams"
                :key="team.name"
                :to="{ name: 'team', params: { TName: team.name } }"
                :color="team.color"
                class="mr-2 mb-2 team-chip"
                variant="outlined"
                label
                size="default"
              >
                <v-icon
                  v-if="team.bounty_value"
                  start
                  icon="mdi-target"
                  color="error"
                  size="x-small"
                  class="mr-1"
                />
                {{ team.name }}
              </v-chip>

              <span v-if="!alliance.teams.length" class="text-caption text-grey font-italic">
                No teams in this alliance.
              </span>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
export default {
  name: "AllianceList",
  data() {
    return {
      loading: false,
      alliances: [],
    };
  },
  created() {
    this.fetchAlliances();
  },
  methods: {
    async fetchAlliances() {
      this.loading = true;
      try {
        const response = await fetch('/api/league/alliances/');
        if (!response.ok) {
          throw new Error('Failed to fetch alliances');
        }
        const data = await response.json();

        this.alliances = data.sort((a, b) => a.name.localeCompare(b.name));
      } catch (error) {
        console.error('Error fetching alliances:', error);
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.alliance-card {
  transition: transform 0.2s, box-shadow 0.2s;
  border-radius: 8px;
  overflow: hidden;
}

.alliance-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
}

.team-chip {
  font-weight: 600;
  border-width: 2px !important;
}
</style>