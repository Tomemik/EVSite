<template>
  <v-dialog v-model="localShowResultsDialog" @update:model-value="close" max-width="800px">
    <v-card>
      <v-card-title>Match Results</v-card-title>
      <v-card-text v-if="detailedMatch">
        <v-select
          v-model="judgeName"
          :items="allTeamNames"
          label="Judge"
        ></v-select>

        <v-select
          v-model="winningSide"
          :items="sides"
          label="Winning Side"
          required
        ></v-select>
        <v-divider></v-divider>

        <v-row>
          <v-col>
            <div v-for="(team, teamIndex) in detailedMatch.sides.team_1" :key="team.team">
              <p style="margin-bottom: 20px"><strong>{{ team.team }}:</strong></p>

              <v-row>
                <v-text-field
                  v-model="teamResults['team_1'][teamIndex].bonuses"
                  label="Bonuses"
                  type="number"
                  min="0"
                  class="ml-2"
                  style="width: 100px;"
                ></v-text-field>
                <v-text-field
                  v-model="teamResults['team_1'][teamIndex].penalties"
                  label="Penalties"
                  type="number"
                  min="0"
                  class="ml-2"
                  style="width: 100px;"
                ></v-text-field>
              </v-row>

              <!-- Tanks Lost -->
              <ul style="list-style-type: none; padding-left: 0;">
                <li v-for="(tank, tankIndex) in team.tanks" :key="tank.id">
                  <v-row align="center">
                    <v-checkbox
                      v-model="tanksLost['team_1'][teamIndex][tankIndex].used"
                      class="mr-2"
                    ></v-checkbox>

                    <v-text-field
                      v-model="tanksLost['team_1'][teamIndex][tankIndex].quantity"
                      :label="tank.tank.name"
                      type="number"
                      min="0"
                      class="ml-2"
                      style="width: 100px; max-width: 100px;"
                    ></v-text-field>
                  </v-row>
                </li>
              </ul>

              <!-- Add Substitute Button -->
              <v-btn @click="addSubstitute('team_1', teamIndex)" color="primary">Add Substitute</v-btn>
              <div v-for="(substitute, subIndex) in substitutes['team_1'][teamIndex]" :key="subIndex">
                <v-row>
                  <v-select
                    v-model="substitute.team"
                    :items="allTeamNames"
                    label="Substitute Team"
                  ></v-select>
                  <v-text-field
                    v-model="substitute.activity"
                    label="Activity"
                    type="number"
                    min="0"
                    class="ml-2"
                    style="width: 100px;"
                  ></v-text-field>
                  <v-btn @click="removeSubstitute('team_1', teamIndex, subIndex)" color="red">Remove</v-btn>
                </v-row>
              </div>
            </div>
          </v-col>

          <v-col class="d-flex justify-center align-center">
            <p style="text-align:center; font-weight: bold;">vs</p>
          </v-col>

          <v-col class="d-flex flex-column align-end">
            <div v-for="(team, teamIndex) in detailedMatch.sides.team_2" :key="team.team">
              <p style="margin-bottom: 20px"><strong>{{ team.team }}:</strong></p>

              <v-row>
                <v-text-field
                  v-model="teamResults['team_2'][teamIndex].bonuses"
                  label="Bonuses"
                  type="number"
                  min="0"
                  class="ml-2"
                  style="width: 100px;"
                ></v-text-field>
                <v-text-field
                  v-model="teamResults['team_2'][teamIndex].penalties"
                  label="Penalties"
                  type="number"
                  min="0"
                  class="ml-2"
                  style="width: 100px;"
                ></v-text-field>
              </v-row>

              <!-- Tanks Lost -->
              <ul style="list-style-type: none; padding-left: 0;">
                <li v-for="(tank, tankIndex) in team.tanks" :key="tank.id">
                  <v-row align="center">
                    <v-checkbox
                      v-model="tanksLost['team_2'][teamIndex][tankIndex].used"
                      class="mr-2"
                    ></v-checkbox>

                    <v-text-field
                      v-model="tanksLost['team_2'][teamIndex][tankIndex].quantity"
                      :label="tank.tank.name"
                      type="number"
                      min="0"
                      class="ml-2"
                      style="width: 100px; max-width: 100px;"
                    ></v-text-field>
                  </v-row>
                </li>
              </ul>

              <!-- Add Substitute Button -->
              <v-btn @click="addSubstitute('team_2', teamIndex)" color="primary">Add Substitute</v-btn>
              <div v-for="(substitute, subIndex) in substitutes['team_2'][teamIndex]" :key="subIndex">
                <v-row>
                  <v-select
                    v-model="substitute.team"
                    :items="allTeamNames"
                    label="Substitute Team"
                  ></v-select>
                  <v-text-field
                    v-model="substitute.activity"
                    label="Activity"
                    type="number"
                    min="0"
                    class="ml-2"
                    style="width: 100px;"
                  ></v-text-field>
                  <v-btn @click="removeSubstitute('team_2', teamIndex, subIndex)" color="red">Remove</v-btn>
                </v-row>
              </div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-btn color="success" @click="submitResults">Submit</v-btn>
        <v-btn color="error" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps(['detailedMatch', 'showResultsDialog', 'allTeamDetails']);
const emit = defineEmits(['update:showResultsDialog', 'postResults']);

const localShowResultsDialog = ref(props.showResultsDialog);
const allTeamNames = ref([]);

watch(() => props.showResultsDialog, (newValue) => {
  localShowResultsDialog.value = newValue;
});

const updateShowResultsDialog = (value) => {
  emit('update:showResultsDialog', value);
};

const close = () => {
  updateShowResultsDialog(false);
};

const sides = ['team_1', 'team_2'];

watch(() => props.allTeamDetails, (newValue) => {
  if (newValue) {
    allTeamNames.value = newValue.map(t => t.name);
  }
});

const judgeName = ref('');
const winningSide = ref('');
const teamResults = ref({});
const tanksLost = ref({});
const substitutes = ref({});

watch(() => props.detailedMatch, (newMatch) => {
  if (newMatch) {
    const sides = ['team_1', 'team_2'];
    sides.forEach((side) => {
      teamResults.value[side] = newMatch.sides[side].map(() => ({ bonuses: 0, penalties: 0 }));
      tanksLost.value[side] = newMatch.sides[side].map((team) =>
        team.tanks.map(() => ({ quantity: 0, notUsed: false, used: true }))
      );
      substitutes.value[side] = newMatch.sides[side].map(() => []);
    });
  }
});

// Add Substitute Method
const addSubstitute = (side, teamIndex) => {
  substitutes.value[side][teamIndex].push({
    team: '',
    team_played_for: { name: props.detailedMatch.sides[side][teamIndex].team },
    activity: 0,
    side: side,
  });
};

// Remove Substitute Method
const removeSubstitute = (side, teamIndex, subIndex) => {
  if (substitutes.value[side][teamIndex].length > 0) {
    substitutes.value[side][teamIndex].splice(subIndex, 1);
  }
};

const submitResults = () => {
  const resultData = {
    match_id: props.detailedMatch.id,
    winning_side: winningSide.value,
    judge_name: judgeName.value,
    team_results: Object.keys(teamResults.value).flatMap((side) =>
      teamResults.value[side].map((result, index) => ({
        team_name: props.detailedMatch.sides[side][index].team,
        bonuses: result.bonuses,
        penalties: result.penalties,
      }))
    ),
    tanks_lost: Object.keys(tanksLost.value).flatMap((side) =>
      tanksLost.value[side].flatMap((teamTanks, teamIndex) =>
        teamTanks.filter(tank => tank.used).map((tank, tankIndex) => ({
          team_name: props.detailedMatch.sides[side][teamIndex].team,
          tank_name: props.detailedMatch.sides[side][teamIndex].tanks[tankIndex].tank.name,
          quantity: tank.quantity,
        }))
      )
    ),
    substitutes: Object.keys(substitutes.value).flatMap((side) =>
      substitutes.value[side].flatMap((substituteList, teamIndex) =>
        substituteList.map(substitute => ({
          team_name: substitute.team,
          team_played_for_name: substitute.team_played_for.name,
          team: { name: substitute.team },
          team_played_for: { name: substitute.team_played_for.name },
          side: substitute.side,
          activity: substitute.activity,
        }))
      )
    ),
  };

  emit('postResults', resultData);
};
</script>

<style scoped>
.v-select {
  margin-bottom: 10px;
}
</style>