<template>
  <v-dialog v-model="localShowResultsDialog" @update:model-value="close" max-width="1200px" persistent>
    <v-card class="rounded-lg">
      <v-toolbar color="primary" density="compact">
        <v-toolbar-title class="text-subtitle-1 font-weight-bold">
          <v-icon start icon="mdi-clipboard-check"></v-icon>
          Match Results & Replays
        </v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-6" style="min-height: 400px; max-height: 75vh; overflow-y: auto;">
        <v-window v-model="currentPhase" disabled>

          <v-window-item value="SETUP">
            <div class="text-center mb-6">
              <v-icon size="64" color="primary" class="mb-4">mdi-file-video</v-icon>
              <h2 class="text-h5 font-weight-bold">Replay Parsing Wizard</h2>
              <p class="text-medium-emphasis">Upload replay files to automatically log match telemetry and kill feeds.</p>
            </div>

            <v-alert
              v-if="verifiedRoundsCount > 0"
              type="success"
              variant="tonal"
              class="mb-6 mx-auto"
              style="max-width: 600px;"
            >
              <v-icon start>mdi-check-circle-outline</v-icon>
              <div>
                <strong>{{ verifiedRoundsCount }} round(s)</strong> have already been parsed and verified for this match.
                <div class="mt-2 d-flex gap-2">
                  <v-btn
                    size="small"
                    color="success"
                    variant="elevated"
                    prepend-icon="mdi-arrow-right"
                    @click="startUploading"
                  >
                    Continue to Round {{ verifiedRoundsCount + 1 }}
                  </v-btn>
                </div>
              </div>
            </v-alert>

            <v-row justify="center" v-if="existingRoundsList.length > 0" class="mb-6">
              <v-col cols="12" sm="6" md="4">
                <div class="text-subtitle-2 font-weight-bold mb-2 text-medium-emphasis">Review Existing Rounds:</div>
                <v-list border class="rounded-lg pa-0">
                  <v-list-item v-for="rd in existingRoundsList" :key="rd.id" :title="'Round ' + rd.round_number" :subtitle="rd.map_name || 'No Map Info'">
                    <template v-slot:append>
                      <v-btn
                        size="small"
                        color="info"
                        variant="tonal"
                        prepend-icon="mdi-pencil"
                        @click="reviewExistingRound(rd)"
                      >
                        Edit Data
                      </v-btn>
                    </template>
                  </v-list-item>
                </v-list>
              </v-col>
            </v-row>

            <v-row justify="center">
              <v-col cols="12" sm="6" md="4">
                <v-select
                  v-model="totalRounds"
                  :items="[1, 2, 3, 4, 5, 6, 7, 8, 9]"
                  label="How many rounds? (inc. Tiebreakers)"
                  variant="outlined"
                  density="comfortable"
                  prepend-inner-icon="mdi-counter"
                ></v-select>

                <v-btn
                  v-if="verifiedRoundsCount === 0"
                  block
                  color="primary"
                  size="large"
                  prepend-icon="mdi-arrow-right"
                  @click="startUploading"
                >
                  Start Uploading
                </v-btn>

                <v-btn
                  block
                  variant="text"
                  color="error"
                  class="mt-4"
                  @click="currentPhase = 'FINAL'"
                >
                  Skip Replays & Enter Manually
                </v-btn>
              </v-col>
            </v-row>
          </v-window-item>

          <v-window-item value="UPLOAD">
            <div
              @dragenter.prevent="isDragging = true"
              @dragover.prevent
              class="position-relative h-100"
              style="min-height: 350px;"
            >
              <v-overlay
                :model-value="isDragging"
                class="align-center justify-center"
                contained
                z-index="10"
                @dragleave.prevent="isDragging = false"
                @drop.prevent="handleDrop"
                @dragover.prevent
              >
                <v-card class="bg-primary text-center pa-8 rounded-xl d-flex flex-column align-center justify-center" style="border: 4px dashed white; pointer-events: none;">
                  <v-icon size="80" class="mb-4">mdi-file-download</v-icon>
                  <div class="text-h4 font-weight-bold">Drop .wrpl files here</div>
                  <div class="text-subtitle-1 mt-2">Files will be appended to the current round</div>
                </v-card>
              </v-overlay>

              <div class="mb-4">
                <h3 class="text-h5 font-weight-bold text-primary">Round {{ currentRound }} of {{ totalRounds }}</h3>
                <p class="text-medium-emphasis">Select or drag & drop all .wrpl POV replays for this round. They will be merged and deduplicated automatically.</p>
              </div>

              <v-alert
                v-if="uploadError"
                type="error"
                variant="tonal"
                class="mb-4"
                closable
                @click:close="uploadError = ''"
              >
                {{ uploadError }}
              </v-alert>

              <v-row>
                <v-col cols="12" md="3">
                  <v-text-field
                    v-model="startTime"
                    label="Start Time (MM:SS)"
                    placeholder="e.g. 3:30"
                    variant="outlined"
                    density="comfortable"
                    prepend-inner-icon="mdi-clock-start"
                    hint="Filters out warmup deaths"
                    persistent-hint
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="9">
                  <v-file-input
                    v-model="replayFiles"
                    label="Select or Drop Replay Files (.wrpl)"
                    variant="outlined"
                    density="comfortable"
                    multiple
                    show-size
                    accept=".wrpl"
                    prepend-inner-icon="mdi-file-multiple"
                    prepend-icon=""
                  ></v-file-input>
                </v-col>
              </v-row>

              <div class="d-flex justify-space-between mt-6">
                <v-btn color="error" variant="text" @click="currentPhase = 'SETUP'">Cancel</v-btn>
                <div>
                  <v-btn
                    color="warning"
                    variant="tonal"
                    class="mr-3"
                    @click="skipRound"
                  >Skip Round {{ currentRound }}</v-btn>
                  <v-btn
                    color="primary"
                    prepend-icon="mdi-cloud-upload"
                    :loading="isUploading"
                    :disabled="replayFiles.length === 0"
                    @click="uploadAndParse"
                  >
                    Parse Round {{ currentRound }}
                  </v-btn>
                </div>
              </div>
            </div>
          </v-window-item>

          <v-window-item value="VERIFY">
            <div class="mb-4 d-flex justify-space-between align-center">
              <div>
                <h3 class="text-h5 font-weight-bold text-primary">Verify Round {{ currentRound }} Data</h3>
                <p class="text-subtitle-1 font-italic text-medium-emphasis mb-0">Map: {{ currentMapName || 'Unknown Map' }} {{ currentMapConfig }}</p>
              </div>
            </div>

            <v-alert
              v-if="verifyError"
              type="error"
              variant="tonal"
              class="mb-4"
              closable
              @click:close="verifyError = ''"
            >
              {{ verifyError }}
            </v-alert>

            <v-row class="mb-4">
              <v-col cols="12" md="3">
                <v-text-field
                  v-model.number="roundStartTime"
                  label="Start Time (s)"
                  type="number"
                  variant="outlined"
                  density="compact"
                  hide-details
                ></v-text-field>
              </v-col>
              <v-col cols="12" md="3">
                <v-text-field
                  v-model.number="roundEndTime"
                  label="End Time (s)"
                  type="number"
                  variant="outlined"
                  density="compact"
                  hide-details
                ></v-text-field>
              </v-col>
              <v-col cols="12" md="3">
                <v-select
                  v-model="roundWinner"
                  :items="[{title: 'Team 1', value: 'team_1'}, {title: 'Team 2', value: 'team_2'}, {title: 'Draw', value: 'draw'}]"
                  label="Round Winner"
                  variant="outlined"
                  density="compact"
                  hide-details
                  clearable
                ></v-select>
              </v-col>
              <v-col cols="12" md="3">
                <v-text-field
                  v-model="winReason"
                  label="Win Reason (e.g. Annihilation, Capture)"
                  variant="outlined"
                  density="compact"
                  hide-details
                ></v-text-field>
              </v-col>
            </v-row>

            <v-card variant="outlined" class="mb-6 border-grey">
              <v-card-title class="bg-grey-lighten-3 py-2 text-subtitle-2 font-weight-bold d-flex justify-space-between align-center">
                <span>Player Spawns</span>
              </v-card-title>
              <v-card-text class="pt-4">
                <v-row>
                  <v-col cols="12" md="6" class="border-e">
                    <div class="d-flex justify-space-between align-center mb-3">
                      <div class="font-weight-bold text-primary">Team 1</div>
                      <v-btn size="x-small" variant="tonal" prepend-icon="mdi-plus" @click="addSpawn('team_1')">Add Spawn</v-btn>
                    </div>
                    <div v-for="spawn in team1Spawns" :key="spawn.id" class="d-flex align-center mb-2 gap-2">
                      <v-text-field v-model="spawn.player" label="Player Name" density="compact" variant="outlined" hide-details></v-text-field>
                      <v-text-field v-model="spawn.vehicle" label="Vehicle" density="compact" variant="outlined" hide-details class="ml-2"></v-text-field>
                      <v-btn icon="mdi-arrow-right-bold" size="small" color="warning" variant="text" v-tooltip="'Move to Team 2'" @click="spawn.team = 'team_2'"></v-btn>
                      <v-btn icon="mdi-delete" size="small" color="error" variant="text" @click="removeSpawn(spawn.id)"></v-btn>
                    </div>
                  </v-col>

                  <v-col cols="12" md="6">
                    <div class="d-flex justify-space-between align-center mb-3">
                      <div class="font-weight-bold text-error">Team 2</div>
                      <v-btn size="x-small" variant="tonal" prepend-icon="mdi-plus" @click="addSpawn('team_2')">Add Spawn</v-btn>
                    </div>
                    <div v-for="spawn in team2Spawns" :key="spawn.id" class="d-flex align-center mb-2 gap-2">
                      <v-btn icon="mdi-arrow-left-bold" size="small" color="warning" variant="text" v-tooltip="'Move to Team 1'" @click="spawn.team = 'team_1'"></v-btn>
                      <v-text-field v-model="spawn.player" label="Player Name" density="compact" variant="outlined" hide-details></v-text-field>
                      <v-text-field v-model="spawn.vehicle" label="Vehicle" density="compact" variant="outlined" hide-details class="ml-2"></v-text-field>
                      <v-btn icon="mdi-delete" size="small" color="error" variant="text" @click="removeSpawn(spawn.id)"></v-btn>
                    </div>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>

            <div class="d-flex justify-space-between align-center mb-2">
              <h4 class="text-subtitle-1 font-weight-bold text-medium-emphasis">Kill Log</h4>
              <v-btn color="primary" size="small" prepend-icon="mdi-plus" variant="tonal" @click="addNewKillRow" :disabled="!!editingItem">
                Add Kill
              </v-btn>
            </div>

            <v-data-table
              :headers="killHeaders"
              :items="pendingKills"
              density="compact"
              class="elevation-1 border rounded mb-6"
              :items-per-page="-1"
            >
              <template v-slot:item.time_s="{ item }">
                <v-text-field
                  v-if="editingItem === (item.raw || item)"
                  v-model="editedKill.time_s"
                  type="number"
                  density="compact"
                  variant="outlined"
                  hide-details
                  style="min-width: 80px;"
                ></v-text-field>
                <span v-else>{{ Number((item.raw || item).time_s || 0).toFixed(1) }}s</span>
              </template>

              <template v-slot:item.attacker="{ item }">
                <div v-if="editingItem === (item.raw || item)" class="d-flex flex-column py-1 gap-1">
                  <v-text-field v-model="editedKill.attacker" density="compact" variant="outlined" hide-details placeholder="Player" class="mb-1"></v-text-field>
                  <v-text-field v-model="editedKill.attacker_veh" density="compact" variant="outlined" hide-details placeholder="Vehicle"></v-text-field>
                </div>
                <div v-else>
                  <strong>{{ (item.raw || item).attacker }}</strong><br>
                  <span class="text-caption text-medium-emphasis">{{ (item.raw || item).attacker_veh }}</span>
                </div>
              </template>

              <template v-slot:item.weapon="{ item }">
                <v-text-field
                  v-if="editingItem === (item.raw || item)"
                  v-model="editedKill.weapon"
                  density="compact"
                  variant="outlined"
                  hide-details
                  style="min-width: 100px;"
                ></v-text-field>
                <span v-else>{{ (item.raw || item).weapon }}</span>
              </template>

              <template v-slot:item.victim="{ item }">
                <div v-if="editingItem === (item.raw || item)" class="d-flex flex-column py-1 gap-1">
                  <v-text-field v-model="editedKill.victim" density="compact" variant="outlined" hide-details placeholder="Player" class="mb-1"></v-text-field>
                  <v-text-field v-model="editedKill.victim_veh" density="compact" variant="outlined" hide-details placeholder="Vehicle"></v-text-field>
                </div>
                <div v-else>
                  <strong>{{ (item.raw || item).victim }}</strong><br>
                  <span class="text-caption text-medium-emphasis">{{ (item.raw || item).victim_veh }}</span>
                </div>
              </template>

              <template v-slot:item.actions="{ item }">
                <div v-if="editingItem === (item.raw || item)" class="d-flex align-center justify-end">
                  <v-btn icon="mdi-check" size="small" color="success" variant="text" v-tooltip="'Save'" @click="saveKill"></v-btn>
                  <v-btn icon="mdi-close" size="small" color="error" variant="text" v-tooltip="'Cancel'" @click="cancelKill"></v-btn>
                </div>
                <div v-else class="d-flex align-center justify-end">
                  <v-btn icon="mdi-pencil" size="small" color="info" variant="text" v-tooltip="'Edit Kill'" :disabled="!!editingItem" @click="editKill(item)"></v-btn>
                  <v-btn icon="mdi-delete" size="small" color="error" variant="text" v-tooltip="'Remove Kill'" :disabled="!!editingItem" @click="removeKill(item)"></v-btn>
                </div>
              </template>
            </v-data-table>

            <div class="d-flex justify-space-between mt-2">
              <v-btn color="error" variant="text" @click="currentPhase = 'UPLOAD'">Back to Upload</v-btn>
              <v-btn
                color="success"
                prepend-icon="mdi-check"
                :loading="isVerifying"
                @click="verifyRound"
                :disabled="!!editingItem"
              >
                Confirm & Save Round {{ currentRound }}
              </v-btn>
            </div>
          </v-window-item>

          <v-window-item value="FINAL">
            <v-form>
              <v-row dense>
                <v-col cols="12" md="4">
                  <v-select
                    v-model="judgeName"
                    :items="allTeamNames"
                    clearable
                    label="Judge"
                    prepend-inner-icon="mdi-gavel"
                    variant="outlined"
                    density="compact"
                  ></v-select>

                  <v-checkbox
                    v-model="judgeIsTest"
                    label="Test Judge"
                    density="compact"
                    hide-details
                    class="mt-1"
                  ></v-checkbox>
                </v-col>

                <v-col cols="12" md="4">
                  <v-select
                    v-model="winningSide"
                    :items="sides"
                    label="Winning Side"
                    required
                    prepend-inner-icon="mdi-trophy"
                    variant="outlined"
                    density="compact"
                  ></v-select>
                </v-col>

                <v-col cols="12" md="4">
                  <v-text-field
                    v-model="roundScore"
                    label="Round Score (X:Y)"
                    placeholder="Winning side 1st"
                    :rules="[roundScoreFormat]"
                    required
                    prepend-inner-icon="mdi-scoreboard"
                    variant="outlined"
                    density="compact"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-divider class="my-6"></v-divider>

              <v-row v-if="detailedMatch">
                <v-col cols="12" md="5">
                  <div class="text-subtitle-1 mb-2 text-center font-weight-bold text-primary">Team 1</div>

                  <div v-for="(team, teamIndex) in detailedMatch.sides.team_1" :key="team.team" class="mb-4">
                    <v-card variant="outlined" class="border-grey">
                      <v-card-item class="bg-grey-lighten-1 py-1">
                        <div class="d-flex align-center">
                          <v-checkbox
                            v-model="teamResults['team_1'][teamIndex].was_present"
                            hide-details
                            density="compact"
                            class="mr-2"
                          ></v-checkbox>
                          <span class="text-subtitle-2 font-weight-bold">{{ team.team }}</span>
                        </div>
                      </v-card-item>

                      <v-divider></v-divider>

                      <v-card-text class="pa-3">
                        <v-row dense class="mb-2">
                          <v-col cols="6">
                            <v-text-field
                              v-model="teamResults['team_1'][teamIndex].bonuses"
                              label="Bonuses"
                              type="number"
                              min="0"
                              variant="outlined"
                              density="compact"
                              hide-details
                              prepend-inner-icon="mdi-star"
                            ></v-text-field>
                          </v-col>
                          <v-col cols="6">
                            <v-text-field
                              v-model="teamResults['team_1'][teamIndex].penalties"
                              label="Penalties"
                              type="number"
                              min="0"
                              variant="outlined"
                              density="compact"
                              hide-details
                              prepend-inner-icon="mdi-alert-circle"
                            ></v-text-field>
                          </v-col>
                        </v-row>

                        <v-divider class="my-3 border-dashed"></v-divider>
                        <div class="text-caption font-weight-bold text-medium-emphasis mb-2">TANKS LOST</div>

                        <div
                          v-for="(tank, tankIndex) in team.tanks"
                          :key="tank.id"
                          class="d-flex align-center mb-1"
                        >
                          <v-checkbox-btn
                            v-model="tanksLost['team_1'][teamIndex][tankIndex].used"
                            density="compact"
                            class="mr-2"
                          ></v-checkbox-btn>

                          <div class="text-body-2 text-truncate flex-grow-1" :class="{'text-decoration-line-through text-disabled': !tanksLost['team_1'][teamIndex][tankIndex].used}">
                            {{ tank.tank.name }}
                          </div>

                          <v-text-field
                            v-model="tanksLost['team_1'][teamIndex][tankIndex].quantity"
                            type="number"
                            min="0"
                            variant="outlined"
                            density="compact"
                            hide-details
                            style="max-width: 70px;"
                            :disabled="!tanksLost['team_1'][teamIndex][tankIndex].used"
                          ></v-text-field>
                        </div>

                        <v-divider class="my-3 border-dashed"></v-divider>

                        <div class="d-flex justify-space-between align-center mb-2">
                          <div class="text-caption font-weight-bold text-medium-emphasis">SUBSTITUTES</div>
                          <v-btn
                            size="x-small"
                            variant="tonal"
                            color="primary"
                            prepend-icon="mdi-account-plus"
                            @click="addSubstitute('team_1', teamIndex)"
                          >Add</v-btn>
                        </div>

                        <div v-for="(substitute, subIndex) in substitutes['team_1'][teamIndex]" :key="subIndex" class="pa-2 rounded mb-2 border">
                          <v-select
                            v-model="substitute.team"
                            :items="allTeamNames"
                            label="Sub Team"
                            density="compact"
                            variant="outlined"
                            hide-details
                            class="mb-2"
                          ></v-select>
                          <div class="d-flex align-center">
                            <v-select
                              v-model="substitute.activity"
                              label="Activity"
                              :items="activityOptions"
                              item-title="title"
                              item-value="value"
                              density="compact"
                              variant="outlined"
                              hide-details
                            ></v-select>
                            <v-btn
                              icon="mdi-delete"
                              size="small"
                              variant="text"
                              color="error"
                              class="ml-2"
                              @click="removeSubstitute('team_1', teamIndex, subIndex)"
                            ></v-btn>
                          </div>
                        </div>

                      </v-card-text>
                    </v-card>
                  </div>
                </v-col>

                <v-col cols="12" md="2" class="d-flex justify-center align-center">
                   <div class="text-h5 text-disabled font-italic font-weight-black">VS</div>
                </v-col>

                <v-col cols="12" md="5">
                  <div class="text-subtitle-1 mb-2 text-center font-weight-bold text-error">Team 2</div>

                  <div v-for="(team, teamIndex) in detailedMatch.sides.team_2" :key="team.team" class="mb-4">
                    <v-card variant="outlined" class="border-grey">
                      <v-card-item class="bg-grey-lighten-1 py-1">
                        <div class="d-flex align-center">
                          <v-checkbox
                            v-model="teamResults['team_2'][teamIndex].was_present"
                            hide-details
                            density="compact"
                            class="mr-2"
                          ></v-checkbox>
                          <span class="text-subtitle-2 font-weight-bold">{{ team.team }}</span>
                        </div>
                      </v-card-item>

                      <v-divider></v-divider>

                      <v-card-text class="pa-3">
                        <v-row dense class="mb-2">
                          <v-col cols="6">
                            <v-text-field
                              v-model="teamResults['team_2'][teamIndex].bonuses"
                              label="Bonuses"
                              type="number"
                              min="0"
                              variant="outlined"
                              density="compact"
                              hide-details
                              prepend-inner-icon="mdi-star"
                            ></v-text-field>
                          </v-col>
                          <v-col cols="6">
                            <v-text-field
                              v-model="teamResults['team_2'][teamIndex].penalties"
                              label="Penalties"
                              type="number"
                              min="0"
                              variant="outlined"
                              density="compact"
                              hide-details
                              prepend-inner-icon="mdi-alert-circle"
                            ></v-text-field>
                          </v-col>
                        </v-row>

                        <v-divider class="my-3 border-dashed"></v-divider>
                        <div class="text-caption font-weight-bold text-medium-emphasis mb-2">TANKS LOST</div>

                        <div
                          v-for="(tank, tankIndex) in team.tanks"
                          :key="tank.id"
                          class="d-flex align-center mb-1"
                        >
                          <v-checkbox-btn
                            v-model="tanksLost['team_2'][teamIndex][tankIndex].used"
                            density="compact"
                            class="mr-2"
                          ></v-checkbox-btn>

                          <div class="text-body-2 text-truncate flex-grow-1" :class="{'text-decoration-line-through text-disabled': !tanksLost['team_2'][teamIndex][tankIndex].used}">
                            {{ tank.tank.name }}
                          </div>

                          <v-text-field
                            v-model="tanksLost['team_2'][teamIndex][tankIndex].quantity"
                            type="number"
                            min="0"
                            variant="outlined"
                            density="compact"
                            hide-details
                            style="max-width: 70px;"
                            :disabled="!tanksLost['team_2'][teamIndex][tankIndex].used"
                          ></v-text-field>
                        </div>

                        <v-divider class="my-3 border-dashed"></v-divider>

                        <div class="d-flex justify-space-between align-center mb-2">
                          <div class="text-caption font-weight-bold text-medium-emphasis">SUBSTITUTES</div>
                          <v-btn
                            size="x-small"
                            variant="tonal"
                            color="primary"
                            prepend-icon="mdi-account-plus"
                            @click="addSubstitute('team_2', teamIndex)"
                          >Add</v-btn>
                        </div>

                        <div v-for="(substitute, subIndex) in substitutes['team_2'][teamIndex]" :key="subIndex" class="pa-2 rounded mb-2 border">
                          <v-select
                            v-model="substitute.team"
                            :items="allTeamNames"
                            label="Sub Team"
                            density="compact"
                            variant="outlined"
                            hide-details
                            class="mb-2"
                          ></v-select>
                          <div class="d-flex align-center">
                            <v-select
                              v-model="substitute.activity"
                              label="Activity"
                              type="number"
                              :items="activityOptions"
                              item-title="title"
                              item-value="value"
                              density="compact"
                              variant="outlined"
                              hide-details
                            ></v-select>
                            <v-btn
                              icon="mdi-delete"
                              size="small"
                              variant="text"
                              color="error"
                              class="ml-2"
                              @click="removeSubstitute('team_2', teamIndex, subIndex)"
                            ></v-btn>
                          </div>
                        </div>

                      </v-card-text>
                    </v-card>
                  </div>
                </v-col>
              </v-row>
            </v-form>
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4" v-if="currentPhase === 'FINAL'">
        <v-btn
          color="info"
          variant="text"
          prepend-icon="mdi-content-copy"
          @click="copyResults"
        >Copy Results</v-btn>

        <v-spacer></v-spacer>

        <template v-if="userStore.groups.some(i => ['commander', 'judge', 'admin'].includes(i.name))">
          <v-btn
            v-if="calcOverride"
            color="warning"
            variant="tonal"
            prepend-icon="mdi-undo"
            @click="revertCalc"
          >Revert Calc</v-btn>

          <v-btn
            :disabled="calcOverride"
            color="success"
            variant="tonal"
            prepend-icon="mdi-calculator"
            @click="calcMatch"
          >Calc</v-btn>

          <v-btn
            :disabled="!canSubmitResults"
            color="success"
            variant="elevated"
            prepend-icon="mdi-check"
            @click="submitResults"
          >Submit Results</v-btn>
        </template>
      </v-card-actions>

      <v-card-actions v-else class="pa-4 justify-end">
        <v-btn color="error" variant="text" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed, inject } from 'vue';
import { useUserStore } from "../config/store.ts";
import { getAuthToken } from "../config/api/user.ts";

const $cookies = inject("$cookies");
const csrfToken = $cookies.get('csrftoken');

const userStore = useUserStore();
const props = defineProps(['detailedMatch', 'showResultsDialog', 'allTeamDetails', 'results', 'calcOverride']);
const emit = defineEmits(['update:showResultsDialog', 'postResults', 'calcMatch', 'revertCalc']);

const localShowResultsDialog = ref(props.showResultsDialog);
const allTeamNames = ref([]);
const calcOverride = ref();

// ==========================================
// DRAG AND DROP LOGIC
// ==========================================
const isDragging = ref(false);

const handleDrop = (event) => {
  isDragging.value = false;
  const droppedFiles = Array.from(event.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.wrpl'));

  if (droppedFiles.length > 0) {
    const newFiles = [...replayFiles.value];
    droppedFiles.forEach(file => {
      // Append only if it hasn't been added already
      if (!newFiles.some(existing => existing.name === file.name)) {
        newFiles.push(file);
      }
    });
    replayFiles.value = newFiles;
  }
};

// ==========================================
// REPLAY WIZARD BASE STATE
// ==========================================
const currentPhase = ref('SETUP');
const totalRounds = ref(3);
const currentRound = ref(1);
const replayFiles = ref([]);
const startTime = ref('5:00');

const isUploading = ref(false);
const isVerifying = ref(false);
const uploadError = ref('');
const verifyError = ref('');

const pendingKills = ref([]);

// NEW FIELDS FOR ROUND WINNER/REASON/TIME
const roundWinner = ref(null);
const winReason = ref('');
const roundStartTime = ref(0);
const roundEndTime = ref(0);

const killHeaders = [
  { title: 'Time', key: 'time_s', sortable: true },
  { title: 'Attacker', key: 'attacker', sortable: true },
  { title: 'Weapon', key: 'weapon', sortable: false },
  { title: 'Victim', key: 'victim', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
];

const skipRound = () => {
  replayFiles.value = [];
  startTime.value = '5:00';
  if (currentRound.value < totalRounds.value) {
    currentRound.value++;
    currentPhase.value = 'UPLOAD';
  } else {
    currentPhase.value = 'FINAL';
  }
};

// ==========================================
// INLINE EDITING STATE & LOGIC
// ==========================================
const editingItem = ref(null);
const editedKill = ref({});
const isAddingNew = ref(false);

const addNewKillRow = () => {
  if (editingItem.value) return;

  const newKill = { time_s: 0, attacker: '', attacker_veh: '', weapon: '', victim: '', victim_veh: '' };
  isAddingNew.value = true;
  editingItem.value = newKill;
  editedKill.value = { ...newKill };

  pendingKills.value.unshift(newKill);
};

const editKill = (item) => {
  if (editingItem.value) return;
  const rawItem = item.raw || item;

  isAddingNew.value = false;
  editingItem.value = rawItem;
  editedKill.value = { ...rawItem };
};

const saveKill = () => {
  if (!editingItem.value) return;

  Object.assign(editingItem.value, editedKill.value);
  pendingKills.value.sort((a, b) => parseFloat(a.time_s || 0) - parseFloat(b.time_s || 0));

  editingItem.value = null;
  isAddingNew.value = false;
};

const cancelKill = () => {
  if (isAddingNew.value) {
    pendingKills.value = pendingKills.value.filter(k => k !== editingItem.value);
  }
  editingItem.value = null;
  isAddingNew.value = false;
};

const removeKill = (item) => {
  const rawItem = item.raw || item;
  pendingKills.value = pendingKills.value.filter(k => k !== rawItem);
};

// ==========================================
// ROUND TRACKING & SPAWN STATE
// ==========================================
const verifiedRoundsCount = ref(0);
const currentMapName = ref('');
const currentMapConfig = ref('');
const spawnsList = ref([]);
const existingRoundsList = ref([]);

const team1Spawns = computed(() => spawnsList.value.filter(s => s.team === 'team_1'));
const team2Spawns = computed(() => spawnsList.value.filter(s => s.team === 'team_2'));

const addSpawn = (team) => {
  spawnsList.value.push({ id: Date.now() + Math.random(), player: '', vehicle: '', team });
};

const removeSpawn = (id) => {
  spawnsList.value = spawnsList.value.filter(s => s.id !== id);
};

// ==========================================
// INIT / RESUME LOGIC
// ==========================================
watch(() => props.showResultsDialog, async (newValue) => {
  localShowResultsDialog.value = newValue;
  if (newValue) {
    currentPhase.value = 'SETUP';
    totalRounds.value = 3;
    replayFiles.value = [];
    startTime.value = '5:00';
    pendingKills.value = [];
    spawnsList.value = [];
    currentMapName.value = '';
    currentMapConfig.value = '';
    roundWinner.value = null;
    winReason.value = '';
    roundStartTime.value = 0;
    roundEndTime.value = 0;
    uploadError.value = '';
    verifyError.value = '';
    isDragging.value = false;

    await fetchExistingRounds();
  }
}, {immediate: true});

const fetchExistingRounds = async () => {
  if (!props.detailedMatch || !props.detailedMatch.id) return;

  try {
    const res = await fetch(`/api/league/matches/${props.detailedMatch.id}/rounds/`, {
      headers: { 'Authorization': getAuthToken() }
    });
    if (res.ok) {
      const data = await res.json();
      const rounds = data.results !== undefined ? data.results : data;

      existingRoundsList.value = rounds;
      const verified = rounds.filter(r => r.is_verified);
      verifiedRoundsCount.value = verified.length;
    } else {
      console.warn("Failed to fetch rounds:", await res.text());
      verifiedRoundsCount.value = 0;
      existingRoundsList.value = [];
    }
  } catch (e) {
    console.error('Error fetching existing rounds:', e);
    verifiedRoundsCount.value = 0;
    existingRoundsList.value = [];
  }
};

const reviewExistingRound = (roundData) => {
  currentRound.value = roundData.round_number;
  currentMapName.value = roundData.map_name || 'Unknown Map';
  currentMapConfig.value = roundData.map_details.mode || 'Unknown';
  roundWinner.value = roundData.winning_team || null;
  winReason.value = roundData.win_reason || '';
  roundStartTime.value = roundData.start_time_s || 0;

  roundEndTime.value = roundData.end_time_s || 0;
  if (!roundEndTime.value && roundData.kills && roundData.kills.length > 0) {
      const killTimes = roundData.kills.map(k => parseFloat(k.time_s || 0));
      roundEndTime.value = Math.ceil(Math.max(...killTimes));
  }

  pendingKills.value = roundData.kills ? [...roundData.kills] : [];

  const rawSpawns = roundData.player_spawns || {};
  spawnsList.value = [];

  ['team_1', 'team_2'].forEach(team => {
    const teamSpawns = rawSpawns[team] || [];
    if (Array.isArray(teamSpawns)) {
      teamSpawns.forEach(s => {
        spawnsList.value.push({ id: Date.now() + Math.random(), player: s.player, vehicle: s.vehicle, team });
      });
    } else {
      Object.entries(teamSpawns).forEach(([player, vehicle]) => {
        spawnsList.value.push({ id: Date.now() + Math.random(), player, vehicle, team });
      });
    }
  });

  currentPhase.value = 'VERIFY';
};

const startUploading = () => {
  currentRound.value = verifiedRoundsCount.value + 1;

  if (currentRound.value > totalRounds.value) {
    currentPhase.value = 'FINAL';
  } else {
    currentPhase.value = 'UPLOAD';
  }
};

// ==========================================
// PARSER RESPONSE HANDLING
// ==========================================
const uploadAndParse = async () => {
  isUploading.value = true;
  uploadError.value = '';

  const formData = new FormData();
  formData.append('round_number', currentRound.value);
  formData.append('start_time', startTime.value);
  replayFiles.value.forEach(file => formData.append('replay_files', file));

  try {
    const response = await fetch(`/api/league/matches/${props.detailedMatch.id}/replays/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken, 'Authorization': getAuthToken() },
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || "Parsing failed.");
    }

    const data = await response.json();

    pendingKills.value = data.round_data?.kills || [];
    currentMapName.value = data.round_data?.map_name || 'Unknown Map';
    roundWinner.value = data.round_data?.winning_team || null;
    winReason.value = data.round_data?.win_reason || '';
    roundStartTime.value = data.round_data?.start_time_s || 0;

    if (pendingKills.value.length > 0) {
      const killTimes = pendingKills.value.map(k => parseFloat(k.time_s || 0));
      roundEndTime.value = Math.ceil(Math.max(...killTimes));
    } else {
      roundEndTime.value = data.round_data?.end_time_s || 0;
    }

    const rawSpawns = data.round_data?.player_spawns || {};
    spawnsList.value = [];
    ['team_1', 'team_2'].forEach(team => {
      const teamSpawns = rawSpawns[team] || [];
      if (Array.isArray(teamSpawns)) {
        teamSpawns.forEach(s => {
          spawnsList.value.push({ id: Date.now() + Math.random(), player: s.player, vehicle: s.vehicle, team });
        });
      } else {
        Object.entries(teamSpawns).forEach(([player, vehicle]) => {
          spawnsList.value.push({ id: Date.now() + Math.random(), player, vehicle, team });
        });
      }
    });

    currentPhase.value = 'VERIFY';
    replayFiles.value = [];
    startTime.value = '5:00';
  } catch (error) {
    uploadError.value = error.message;
  } finally {
    isUploading.value = false;
  }
};

// ==========================================
// VERIFY PAYLOAD
// ==========================================
const verifyRound = async () => {
  isVerifying.value = true;
  verifyError.value = '';

  const repackedSpawns = { team_1: [], team_2: [] };
  spawnsList.value.forEach(s => {
    repackedSpawns[s.team].push({ player: s.player, vehicle: s.vehicle });
  });

  try {
    const response = await fetch(`/api/league/matches/${props.detailedMatch.id}/replays/${currentRound.value}/verify/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Authorization': getAuthToken(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        kills: pendingKills.value,
        spawns: repackedSpawns,
        winning_team: roundWinner.value,
        win_reason: winReason.value,
        start_time_s: roundStartTime.value,
        end_time_s: roundEndTime.value
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || "Failed to verify round.");
    }

    await fetchExistingRounds();

    if (currentRound.value <= verifiedRoundsCount.value) {
      currentPhase.value = 'SETUP';
    } else if (currentRound.value < totalRounds.value) {
      currentRound.value++;
      currentPhase.value = 'UPLOAD';
    } else {
      currentPhase.value = 'FINAL';
    }
  } catch (error) {
    verifyError.value = error.message;
  } finally {
    isVerifying.value = false;
  }
};

// ==========================================
// AUTO FILL MATCH RESULTS
// ==========================================
watch(currentPhase, (newPhase) => {
  if (newPhase === 'FINAL' && existingRoundsList.value && existingRoundsList.value.length > 0) {
    autoFillResults();
  }
});

const autoFillResults = () => {
  let t1Wins = 0;
  let t2Wins = 0;

  Object.keys(tanksLost.value).forEach(side => {
    tanksLost.value[side].forEach(teamList => {
      teamList.forEach(t => t.quantity = 0);
    });
  });
  Object.keys(teamResults.value).forEach(side => {
    teamResults.value[side].forEach(team => {
      team.bonuses = 0;
    });
  });

  existingRoundsList.value.forEach(round => {
    if (round.winning_team === 'team_1') t1Wins++;
    if (round.winning_team === 'team_2') t2Wins++;

    if (round.kills && Array.isArray(round.kills)) {
      round.kills.forEach(kill => {
        let victimSide = null;
        if (round.player_spawns && round.player_spawns.team_1 && round.player_spawns.team_1.some(s => s.player === kill.victim)) {
          victimSide = 'team_1';
        } else if (round.player_spawns && round.player_spawns.team_2 && round.player_spawns.team_2.some(s => s.player === kill.victim)) {
          victimSide = 'team_2';
        }

        if (victimSide && tanksLost.value[victimSide]) {
          let matchingTanks = [];
          tanksLost.value[victimSide].forEach(teamList => {
            teamList.forEach(t => {
              if (t.name === kill.victim_veh) {
                matchingTanks.push(t);
              }
            });
          });

          if (matchingTanks.length > 0) {
            matchingTanks.sort((a, b) => a.quantity - b.quantity);
            matchingTanks[0].quantity++;
          }
        }
      });
    }

    if (round.winning_team && round.winning_team !== 'draw' && round.kills && round.kills.length > 0) {
      const killTimes = round.kills.map(k => parseFloat(k.time_s || 0));
      const lastKillTime = Math.max(...killTimes);
      const roundStart = round.start_time_s || 300;
      const finalEnd = round.end_time_s || lastKillTime;
      const combatDuration = finalEnd - roundStart;

      if (combatDuration <= 300 && teamResults.value[round.winning_team]) {
        teamResults.value[round.winning_team].forEach(team => {
          team.bonuses += 1;
        });
      }
    }
  });

  if (t1Wins > t2Wins) {
    winningSide.value = 'team_1';
    roundScore.value = `${t1Wins}:${t2Wins}`;
  } else if (t2Wins > t1Wins) {
    winningSide.value = 'team_2';
    roundScore.value = `${t2Wins}:${t1Wins}`;
  } else {
    roundScore.value = `${t1Wins}:${t2Wins}`;
  }
};

// ==========================================
// EXISTING MATCH RESULT STATE & LOGIC
// ==========================================
watch(() => props.calcOverride, (newValue) => {
  calcOverride.value = newValue;
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
const judgeIsTest = ref(false);
const winningSide = ref('');
const teamResults = ref({});
const tanksLost = ref({});
const substitutes = ref({});
const resultData = ref();
const roundScore = ref('');

const roundScoreFormat = (value) => {
  const regex = /^\d+:\d+$/;
  if (!value) {
    return true;
  }
  return regex.test(value) || 'Invalid score format. Use x:y';
};

const canSubmitResults = computed(() => {
  const roundScoreRegex = /^\d+:\d+$/;
  return winningSide.value && roundScoreRegex.test(roundScore.value);
});

const revertCalc = async () => {
  try {
    await emit('revertCalc', props.detailedMatch.id);
  } catch (error) {
    console.error('Error reverting calculation:', error);
  }
};

watch(() => props.detailedMatch, async (newMatch) => {
  if (newMatch) {
    const sides = ['team_1', 'team_2'];
    sides.forEach((side) => {
      teamResults.value[side] = newMatch.sides[side].map(() => ({ bonuses: 0, penalties: 0, was_present: true}));
      tanksLost.value[side] = newMatch.sides[side].map((team) =>
        team.tanks.map((tank) => ({ quantity: 0, used: true, name:tank.tank.name }))
      );
      substitutes.value[side] = newMatch.sides[side].map(() => []);
    });

    if (localShowResultsDialog.value) {
      await fetchExistingRounds();
    }
  }
});

watch(() => props.results, (newResults) => {
  if (newResults) {
    const sides = ['team_1', 'team_2'];
    sides.forEach((side) => {
      teamResults.value[side] = props.detailedMatch.sides[side].map((team) => {
        const existingResult = newResults?.team_results?.find(
          (result) => result.team === team.team
        ) || {};
        return {
          bonuses: existingResult.bonuses || 0,
          penalties: existingResult.penalties || 0,
          was_present: existingResult.was_present,
        };
      });
      tanksLost.value[side] = props.detailedMatch.sides[side].map((team) => {
        return team.tanks.map((tank) => {
          const lostTankData = newResults?.tanks_lost?.find(
            (lostTank) => lostTank.team === team.team && lostTank.tank === tank.tank.name
          );
          const index = newResults?.tanks_lost?.findIndex(
            (lostTank) => lostTank.team === team.team && lostTank.tank === tank.tank.name
          );

          if (index !== -1 && newResults.tanks_lost) {
              newResults.tanks_lost[index] = {}
          }

          if (lostTankData) {
            return {
              quantity: lostTankData.quantity,
              used: true,
              name: tank.tank.name,
            }
          } else {
            return {
              quantity: 0,
              used: false,
              name: tank.tank.name
            };
          }
        }).flat();
      });
      substitutes.value[side] = props.detailedMatch.sides[side].map((team) => {
        return (
          newResults?.substitutes?.filter(
            (sub) => sub.team_played_for === team.team
          ) || []
        );
      });
    });
  }

  judgeIsTest.value = props.results?.judge_is_test || false;
  winningSide.value = props.results?.winning_side || '';
  judgeName.value = props.results?.judge || '';
  roundScore.value = props.results?.round_score || '';
});

const addSubstitute = (side, teamIndex) => {
  substitutes.value[side][teamIndex].push({
    team: '',
    team_played_for: { name: props.detailedMatch.sides[side][teamIndex].team },
    activity: null,
    side: side,
  });
};

const removeSubstitute = (side, teamIndex, subIndex) => {
  if (substitutes.value[side][teamIndex].length > 0) {
    substitutes.value[side][teamIndex].splice(subIndex, 1);
  }
};

const submitResults = () => {
  resultData.value = {
    match_id: props.detailedMatch.id,
    winning_side: winningSide.value,
    judge_name: judgeName.value || '',
    judge_is_test: judgeIsTest.value,
    round_score: roundScore.value,
    team_results: Object.keys(teamResults.value).flatMap((side) =>
      teamResults.value[side].map((result, index) => ({
        team_name: props.detailedMatch.sides[side][index].team,
        bonuses: result.bonuses,
        penalties: result.penalties,
        was_present: result.was_present,
      }))
    ),
    tanks_lost: Object.keys(tanksLost.value).flatMap((side) =>
      tanksLost.value[side].flatMap((teamTanks, teamIndex) =>
        teamTanks.filter(tank => tank.used === true).map((tank) => ({
          team_name: props.detailedMatch.sides[side][teamIndex].team,
          tank_name: tank.name,
          quantity: tank.quantity,
          used: tank.used,
        }))
      )
    ),
    substitutes: Object.keys(substitutes.value).flatMap((side) =>
      substitutes.value[side].flatMap((substituteList, teamIndex) =>
        substituteList.map(substitute => ({
          team_name: substitute.team,
          team_played_for_name: substitute.team_played_for.name || substitute.team_played_for,
          team: { name: substitute.team },
          team_played_for: { name: substitute.team_played_for.name || substitute.team_played_for },
          side: substitute.side,
          activity: substitute.activity,
        }))
      )
    ),
  };

  emit('postResults', resultData.value);
};

const prepResults = () => {
    resultData.value = {
    match_id: props.detailedMatch.id,
    winning_side: winningSide.value,
    judge_name: judgeName.value || '',
    judge_is_test: judgeIsTest.value,
    round_score: roundScore.value,
    team_results: Object.keys(teamResults.value).flatMap((side) =>
      teamResults.value[side].map((result, index) => ({
        team_name: props.detailedMatch.sides[side][index].team,
        bonuses: result.bonuses,
        penalties: result.penalties,
        side: props.detailedMatch.sides[side][index].side,
        was_present: result.was_present,
      }))
    ),
    tanks_lost: Object.keys(tanksLost.value).flatMap((side) =>
      tanksLost.value[side].flatMap((teamTanks, teamIndex) =>
        teamTanks.filter(tank => tank.used === true).map((tank) => ({
          team_name: props.detailedMatch.sides[side][teamIndex].team,
          tank_name: tank.name,
          quantity: tank.quantity,
          used: tank.used,
        }))
      )
    ),
    substitutes: Object.keys(substitutes.value).flatMap((side) =>
      substitutes.value[side].flatMap((substituteList, teamIndex) =>
        substituteList.map(substitute => ({
          team_name: substitute.team,
          team_played_for_name: substitute.team_played_for.name || substitute.team_played_for,
          team: { name: substitute.team },
          team_played_for: { name: substitute.team_played_for.name || substitute.team_played_for },
          side: substitute.side,
          activity: substitute.activity,
        }))
      )
    ),
  };
}

const gamemodeOptions = [
  { value: 'annihilation', title: 'Annihilation' },
  { value: 'domination', title: 'Domination' },
  { value: 'flag_tank', title: 'Flag Tank' }
];

const modeOptions = [
  { value: 'traditional', title: 'Traditional' },
  { value: 'advanced', title: 'Advanced' },
  { value: 'evolved', title: 'Evolved' }
];

const moneyRulesOptions = [
  { value: 'money_rule', title: 'Money Rule' },
  { value: 'even_split', title: 'Even Split' },
  { value: 'none', title: 'None' }
];

const activityOptions = [
  { value: '1', title: 'Low' },
  { value: '2', title: 'Medium' },
  { value: '3', title: 'High' }
];

const getTitleByValue = (options, value) => {
  const option = options.find(opt => opt.value === value);
  return option ? option.title : value;
};

const copyResults = () => {
  prepResults()
  const match = resultData.value;

  const formatTeamDetails = (teams, tanksLost, substitutes, side) => {
    return teams
      .filter(team => team.side === side)
      .map((team) => {
        const teamTanksLost = tanksLost
          .filter(tank => tank.used === true)
          .filter(tank => tank.team_name === team.team_name)
          .map(tank => `x${tank.quantity} - ${tank.tank_name}`)
          .join('\n');

        const teamSubstitutes = substitutes
          .filter(sub => sub.team_played_for.name === team.team_name)
          .map(sub => `- ${sub.team.name} (${getTitleByValue(activityOptions, String(sub.activity))})`)
          .join('\n');

        const attendanceNote = team.was_present ? '' : '**(No Show)**';

        return `
**${team.team_name}** ${attendanceNote}
Bonuses: ${team.bonuses}
Penalties: ${team.penalties}
Substitutes:
${teamSubstitutes || 'None'}

Tanks Lost:
${teamTanksLost || 'None'}
        `;
      })
      .join('\n');
  };

  const winningSideTeams = match.team_results
    .filter(team => props.detailedMatch.sides[winningSide.value].some(sideTeam => sideTeam.team === team.team_name))
    .map(team => team.team_name)
    .join(' + ');

  const matchResults = `
${formatDateTimeForCopy(props.detailedMatch.datetime)}
${getTitleByValue(gamemodeOptions, props.detailedMatch.gamemode)}, ${getTitleByValue(modeOptions, props.detailedMatch.mode)}, Bo${props.detailedMatch.best_of_number}, ${props.detailedMatch.map_selection}
${getTitleByValue(moneyRulesOptions, props.detailedMatch.money_rules)}
${props.detailedMatch.special_rules || 'None'}

Judge: ${judgeName.value || 'N/A'}

**${winningSideTeams} win ${roundScore.value}**

${formatTeamDetails(match.team_results, match.tanks_lost, match.substitutes, 'team_1')}

--- vs. ---

${formatTeamDetails(match.team_results, match.tanks_lost, match.substitutes, 'team_2')}
  `;

  navigator.clipboard.writeText(matchResults.trim()).then(() => {
    alert('Match results copied to clipboard!');
  }).catch(err => {
    console.error('Failed to copy match results:', err);
  });
};

const formatDateTimeForCopy = (datetime) => {
  const date = new Date(datetime);

  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const dayName = days[date.getUTCDay()];

  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const monthName = months[date.getUTCMonth()];

  const day = date.getUTCDate();
  const ordinal = (n) => {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return s[(v - 20) % 10] || s[v] || s[0];
  };
  const dayWithOrdinal = `${day}${ordinal(day)}`;

  const year = date.getUTCFullYear();

  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');

  return `${dayName}, ${monthName} ${dayWithOrdinal}, ${year} - ${hours}:${minutes} UTC`;
};

const calcMatch = async () => {
  try {
    await emit('calcMatch', props.detailedMatch.id);
  } catch (error) {
    console.error('Error calculating match:', error);
  }
};
</script>

<style scoped>
.border-grey {
  border-color: #BDBDBD !important;
}
.border-dashed {
  border-style: dashed;
}
</style>