<template>
  <v-container fluid class="auction-page pa-3 pa-md-5">
    <!-- ============================================================
         PAGE HEADER
    ============================================================= -->
    <v-row align="center" class="mb-3">
      <v-col cols="12" md="7">
        <div class="text-h4 font-weight-bold">
          Auctions
        </div>

        <div class="text-body-2 text-medium-emphasis mt-1">
          Unpurchased imports accumulate here and are auctioned every
          {{ collectingCycle?.batch_target ?? 8 }} import cycles.
        </div>
      </v-col>

      <v-col
        cols="12"
        md="5"
        class="d-flex justify-md-end align-center ga-2"
      >
        <v-chip
          v-if="team.name"
          color="success"
          variant="tonal"
          size="large"
        >
          <v-icon start>
            mdi-cash
          </v-icon>

          {{ team.name }}:
          {{ formatMoney(team.balance) }}
        </v-chip>

        <v-btn
          icon="mdi-refresh"
          variant="text"
          :loading="loading"
          @click="refreshEverything"
        />
      </v-col>
    </v-row>

    <!-- ============================================================
         ERROR
    ============================================================= -->
    <v-alert
      v-if="loadError"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
      @click:close="loadError = ''"
    >
      {{ loadError }}
    </v-alert>

    <!-- ============================================================
         NO ACTIVE AUCTION
    ============================================================= -->
    <v-alert
      v-if="!activeCycle && !loading"
      type="info"
      variant="tonal"
      class="mb-4"
    >
      There is currently no auction in voting, scheduled, or live state.
      The next auction pool is still collecting expired imports below.
    </v-alert>

    <!-- ============================================================
         ACTIVE AUCTION
    ============================================================= -->
    <template v-if="activeCycle">
      <!-- ==========================================================
           ACTIVE HEADER
      =========================================================== -->
      <v-card class="mb-5" elevation="3">
        <v-card-text>
          <v-row align="center">
            <v-col cols="12" md="7">
              <div class="d-flex align-center flex-wrap ga-2">
                <div class="text-h5 font-weight-bold">
                  Auction #{{ activeCycle.id }}
                </div>

                <v-chip
                  :color="statusColor(activeCycle.status)"
                  variant="flat"
                  size="small"
                >
                  {{ statusLabel(activeCycle.status) }}
                </v-chip>
              </div>

              <div
                v-if="activeCycle.status === 'voting'"
                class="text-body-2 text-medium-emphasis mt-2"
              >
                Vote for the tanks you want to enter the auction.
                Each school receives
                {{ activeCycle.max_votes_per_team }}
                votes.
              </div>

              <div
                v-else-if="
                  activeCycle.status === 'scheduled'
                  && !isEffectivelyLive(activeCycle)
                "
                class="text-body-2 text-medium-emphasis mt-2"
              >
                Voting has finished. The selected tanks are waiting
                for the auction to begin.
              </div>

              <div
                v-else-if="isEffectivelyLive(activeCycle)"
                class="text-body-2 text-medium-emphasis mt-2"
              >
                Bidding is live. Each lot has its own closing time.
                Late bids can extend that specific lot.
              </div>
            </v-col>

            <v-col
              cols="12"
              md="5"
              class="text-md-right"
            >
              <!-- Voting countdown -->
              <template v-if="activeCycle.status === 'voting'">
                <div class="text-caption text-medium-emphasis">
                  Voting closes in
                </div>

                <div class="text-h5 font-weight-bold">
                  {{ countdown(activeCycle.voting_ends_at) }}
                </div>

                <div class="text-caption mt-1">
                  {{ formatDateTime(activeCycle.voting_ends_at) }}
                </div>
              </template>

              <!-- Scheduled countdown -->
              <template
                v-else-if="
                  activeCycle.status === 'scheduled'
                  && !isEffectivelyLive(activeCycle)
                "
              >
                <div class="text-caption text-medium-emphasis">
                  Auction begins in
                </div>

                <div class="text-h5 font-weight-bold">
                  {{ countdown(activeCycle.auction_starts_at) }}
                </div>

                <div class="text-caption mt-1">
                  {{ formatDateTime(activeCycle.auction_starts_at) }}
                </div>
              </template>

              <!-- Live -->
              <template v-else-if="isEffectivelyLive(activeCycle)">
                <div class="text-caption text-medium-emphasis">
                  Auction status
                </div>

                <div class="text-h5 font-weight-bold text-success">
                  LIVE
                </div>

                <div class="text-caption mt-1">
                  Lots close independently
                </div>
              </template>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- ==========================================================
           VOTING
      =========================================================== -->
      <template v-if="activeCycle.status === 'voting'">
        <!-- Vote budget -->
        <v-card class="mb-4" variant="outlined">
          <v-card-text>
            <v-row align="center">
              <v-col cols="12" md="6">
                <div class="text-subtitle-1 font-weight-bold">
                  Your School's Votes
                </div>

                <div class="text-body-2 text-medium-emphasis">
                  You may vote for the same tank multiple times,
                  up to the number of copies available.
                </div>
              </v-col>

              <v-col
                cols="12"
                md="6"
                class="text-md-right"
              >
                <div class="text-h5 font-weight-bold">
                  {{ activeCycle.my_votes_used }}
                  /
                  {{ activeCycle.max_votes_per_team }}
                </div>

                <div class="text-caption text-medium-emphasis">
                  {{ activeCycle.my_votes_remaining }} remaining
                </div>
              </v-col>
            </v-row>

            <v-progress-linear
              class="mt-3"
              height="8"
              rounded
              :model-value="voteProgress(activeCycle)"
              color="primary"
            />
          </v-card-text>
        </v-card>

        <!-- ========================================================
             VOTING FILTERS / SORTING
        ========================================================= -->
        <v-card class="mb-4" variant="outlined">
          <v-card-text>
            <v-row dense align="center">
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="votingSearch"
                  label="Search tanks"
                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  density="compact"
                  clearable
                  hide-details
                />
              </v-col>

              <v-col cols="12" sm="6" md="2">
                <v-select
                  v-model="votingTypeFilter"
                  :items="votingTankTypes"
                  label="Type"
                  variant="outlined"
                  density="compact"
                  clearable
                  hide-details
                />
              </v-col>

              <v-col cols="12" sm="6" md="2">
                <v-select
                  v-model="votingRankFilter"
                  :items="votingRanks"
                  label="Rank"
                  variant="outlined"
                  density="compact"
                  clearable
                  hide-details
                />
              </v-col>

              <v-col cols="12" md="4">
                <v-select
                  v-model="votingSort"
                  :items="votingSortOptions"
                  item-title="title"
                  item-value="value"
                  label="Sort by"
                  variant="outlined"
                  density="compact"
                  hide-details
                />
              </v-col>

              <v-col cols="12">
                <div class="d-flex align-center flex-wrap ga-4">
                  <v-checkbox
                    v-model="onlyMyVotes"
                    label="Only tanks my school voted for"
                    density="compact"
                    hide-details
                  />

                  <v-chip
                    size="small"
                    variant="tonal"
                  >
                    {{ filteredVotingCandidates.length }}
                    /
                    {{ activeCycle.candidates.length }}
                    tanks shown
                  </v-chip>

                  <v-btn
                    v-if="hasVotingFilters"
                    size="small"
                    variant="text"
                    prepend-icon="mdi-filter-remove"
                    @click="clearVotingFilters"
                  >
                    Clear filters
                  </v-btn>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Candidate cards -->
        <v-row>
          <v-col
            v-for="candidate in filteredVotingCandidates"
            :key="candidate.id"
            cols="12"
            sm="6"
            lg="4"
            xl="3"
          >
            <v-card
              class="h-100 d-flex flex-column"
              :class="{
                'selected-candidate':
                  candidate.my_team_votes > 0
              }"
              elevation="2"
            >
              <v-card-title class="pb-1">
                <div class="text-h6 text-wrap">
                  {{ candidate.tank.name }}
                </div>
              </v-card-title>

              <v-card-subtitle>
                BR {{ candidate.tank.battle_rating }}
                · Rank {{ candidate.tank.rank }}
                · {{ candidate.tank.type }}
              </v-card-subtitle>

              <v-card-text class="flex-grow-1">
                <div
                  class="d-flex justify-space-between align-center mb-2"
                >
                  <span class="text-medium-emphasis">
                    Copies available
                  </span>

                  <v-chip size="small">
                    ×{{ candidate.quantity }}
                  </v-chip>
                </div>

                <div
                  class="d-flex justify-space-between align-center mb-2"
                >
                  <span class="text-medium-emphasis">
                    Total votes
                  </span>

                  <strong class="text-h6">
                    {{ candidate.vote_count }}
                  </strong>
                </div>

                <div
                  class="d-flex justify-space-between align-center mb-4"
                >
                  <span class="text-medium-emphasis">
                    Your votes
                  </span>

                  <strong>
                    {{ candidate.my_team_votes }}
                    /
                    {{ candidate.max_team_votes_here }}
                  </strong>
                </div>

                <!-- Allocation controls -->
                <div
                  class="d-flex justify-center align-center ga-4"
                >
                  <v-btn
                    icon="mdi-minus"
                    size="small"
                    color="error"
                    variant="tonal"
                    :loading="voteLoadingCandidate === candidate.id"
                    :disabled="
                      !isCommander
                      || candidate.my_team_votes <= 0
                      || voteLoadingCandidate !== null
                    "
                    @click="removeCandidateVote(candidate)"
                  />

                  <div
                    class="text-h5 font-weight-bold vote-number"
                  >
                    {{ candidate.my_team_votes }}
                  </div>

                  <v-btn
                    icon="mdi-plus"
                    size="small"
                    color="success"
                    variant="tonal"
                    :loading="voteLoadingCandidate === candidate.id"
                    :disabled="
                      !isCommander
                      || activeCycle.my_votes_remaining <= 0
                      || candidate.my_team_votes >= candidate.max_team_votes_here
                      || voteLoadingCandidate !== null
                    "
                    @click="addCandidateVote(candidate)"
                  />
                </div>

                <div
                  v-if="
                    candidate.my_team_votes
                    >= candidate.max_team_votes_here
                  "
                  class="text-caption text-center text-medium-emphasis mt-2"
                >
                  Maximum allocation for this tank reached.
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-alert
          v-if="activeCycle.candidates.length === 0"
          type="info"
          variant="tonal"
        >
          No unpurchased tanks were collected for this auction.
        </v-alert>

        <v-alert
          v-else-if="filteredVotingCandidates.length === 0"
          type="info"
          variant="tonal"
        >
          No tanks match the selected filters.
        </v-alert>
      </template>

      <!-- ==========================================================
           SCHEDULED
      =========================================================== -->
      <template
        v-if="
          activeCycle.status === 'scheduled'
          && !isEffectivelyLive(activeCycle)
        "
      >
        <div class="text-h5 font-weight-bold mb-3">
          Selected Auction Lots
        </div>

        <v-card variant="outlined">
          <v-table>
            <thead>
              <tr>
                <th>Lot</th>
                <th>Tank</th>
                <th>Starting Bid</th>
                <th>Starts</th>
                <th>Normal Close</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="lot in activeCycle.lots"
                :key="lot.id"
              >
                <td>
                  #{{ lot.position }}
                </td>

                <td class="font-weight-bold">
                  {{ lot.tank.name }}
                </td>

                <td>
                  {{ formatMoney(lot.starting_bid) }}
                </td>

                <td>
                  {{ formatDateTime(activeCycle.auction_starts_at) }}
                </td>

                <td>
                  {{ formatDateTime(lot.ends_at) }}
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card>

        <v-alert
          v-if="activeCycle.lots.length === 0"
          type="warning"
          variant="tonal"
          class="mt-3"
        >
          No tanks qualified for this auction.
        </v-alert>
      </template>

      <!-- ==========================================================
           LIVE AUCTION
      =========================================================== -->
      <template v-if="isEffectivelyLive(activeCycle)">
        <div
          class="d-flex align-center justify-space-between flex-wrap ga-2 mb-3"
        >
          <div>
            <div class="text-h5 font-weight-bold">
              Live Lots
            </div>

            <div class="text-caption text-medium-emphasis">
              Live data refreshes automatically.
            </div>
          </div>

          <v-chip
            color="success"
            variant="tonal"
          >
            <v-icon
              start
              size="small"
            >
              mdi-access-point
            </v-icon>

            Live polling
          </v-chip>
        </div>

        <v-row>
          <v-col
            v-for="lot in activeCycle.lots"
            :key="lot.id"
            cols="12"
            md="6"
            xl="4"
          >
            <v-card
              class="h-100 lot-card"
              :class="{
                'leading-lot': isMyTeamLeading(lot),
                'closed-lot': isLotClosed(lot),
              }"
              elevation="3"
            >
              <v-card-title
                class="d-flex justify-space-between align-center"
              >
                <span>
                  Lot #{{ lot.position }}
                </span>

                <v-chip
                  v-if="lot.finalized_at"
                  color="grey"
                  size="small"
                >
                  Closed
                </v-chip>

                <v-chip
                  v-else-if="isLotClosed(lot)"
                  color="warning"
                  size="small"
                >
                  Finalizing
                </v-chip>

                <v-chip
                  v-else-if="lot.was_extended"
                  color="warning"
                  size="small"
                >
                  Extended
                </v-chip>

                <v-chip
                  v-else
                  color="success"
                  size="small"
                >
                  Live
                </v-chip>
              </v-card-title>

              <v-divider />

              <v-card-text>
                <!-- Tank -->
                <div class="text-h5 font-weight-bold mb-1">
                  {{ lot.tank.name }}
                </div>

                <div class="text-body-2 text-medium-emphasis mb-4">
                  BR {{ lot.tank.battle_rating }}
                  · Rank {{ lot.tank.rank }}
                  · {{ lot.tank.type }}
                </div>

                <!-- Timer -->
                <div
                  class="timer-box text-center pa-3 rounded mb-4"
                >
                  <div class="text-caption text-medium-emphasis">
                    {{
                      isLotClosed(lot)
                        ? "Lot closed"
                        : "Time remaining"
                    }}
                  </div>

                  <div
                    class="text-h4 font-weight-bold"
                    :class="{
                      'text-error':
                        !isLotClosed(lot)
                        && millisecondsUntil(lot.ends_at) <= 60000,

                      'text-warning':
                        !isLotClosed(lot)
                        && millisecondsUntil(lot.ends_at) > 60000
                        && millisecondsUntil(lot.ends_at) <= 300000,
                    }"
                  >
                    {{
                      isLotClosed(lot)
                        ? "00:00"
                        : shortCountdown(lot.ends_at)
                    }}
                  </div>

                  <div class="text-caption text-medium-emphasis">
                    {{ formatTime(lot.ends_at) }}

                    <span v-if="lot.was_extended">
                      · extended by bidding
                    </span>
                  </div>
                </div>

                <!-- Bid state -->
                <div
                  class="d-flex justify-space-between mb-2"
                >
                  <span class="text-medium-emphasis">
                    Starting bid
                  </span>

                  <span>
                    {{ formatMoney(lot.starting_bid) }}
                  </span>
                </div>

                <div
                  class="d-flex justify-space-between mb-2"
                >
                  <span class="text-medium-emphasis">
                    Current bid
                  </span>

                  <strong class="text-h6">
                    {{
                      lot.current_bid !== null
                        ? formatMoney(lot.current_bid)
                        : "No bids"
                    }}
                  </strong>
                </div>

                <div
                  class="d-flex justify-space-between mb-2"
                >
                  <span class="text-medium-emphasis">
                    Leader
                  </span>

                  <span
                    :class="{
                      'text-success font-weight-bold':
                        isMyTeamLeading(lot)
                    }"
                  >
                    {{ lot.current_bidder ?? "—" }}
                  </span>
                </div>

                <div
                  class="d-flex justify-space-between mb-4"
                >
                  <span class="text-medium-emphasis">
                    Bids
                  </span>

                  <span>
                    {{ lot.bid_count }}
                  </span>
                </div>

                <!-- Finalized winner -->
                <v-alert
                  v-if="lot.finalized_at && lot.winner"
                  type="success"
                  variant="tonal"
                  density="compact"
                  class="mb-3"
                >
                  Won by
                  <strong>{{ lot.winner }}</strong>
                  for
                  <strong>
                    {{ formatMoney(lot.winning_bid ?? 0) }}
                  </strong>
                </v-alert>

                <v-alert
                  v-else-if="lot.finalized_at"
                  type="info"
                  variant="tonal"
                  density="compact"
                  class="mb-3"
                >
                  Lot closed without a bid.
                </v-alert>

                <v-alert
                  v-else-if="isLotClosed(lot)"
                  type="warning"
                  variant="tonal"
                  density="compact"
                  class="mb-3"
                >
                  Bidding has closed. Waiting for finalization.
                </v-alert>

                <!-- Bid form -->
                <template v-if="!isLotClosed(lot)">
                  <v-divider class="mb-4" />

                  <div class="text-caption text-medium-emphasis mb-1">
                    Minimum next bid:
                    <strong>
                      {{ formatMoney(lot.minimum_next_bid ?? lot.starting_bid) }}
                    </strong>
                  </div>

                  <div class="d-flex ga-2 align-start">
                    <v-text-field
                      v-model="bidAmounts[lot.id]"
                      label="Your bid"
                      type="number"
                      variant="outlined"
                      density="compact"
                      hide-details="auto"
                      prefix="$"
                      :min="lot.minimum_next_bid ?? lot.starting_bid"
                      :step="lot.minimum_increment"
                      :disabled="!isCommander"
                      @keyup.enter="submitBid(lot)"
                    />

                    <v-btn
                      color="success"
                      height="40"
                      :loading="bidLoadingLot === lot.id"
                      :disabled="
                        !canSubmitBid(lot)
                        || bidLoadingLot !== null
                      "
                      @click="submitBid(lot)"
                    >
                      Bid
                    </v-btn>
                  </div>

                  <div
                    v-if="isMyTeamLeading(lot)"
                    class="text-caption text-success mt-2"
                  >
                    <v-icon size="small">
                      mdi-crown
                    </v-icon>

                    Your school currently leads this lot.
                  </div>

                  <div
                    v-if="!isCommander"
                    class="text-caption text-medium-emphasis mt-2"
                  >
                    Only commanders may place bids.
                  </div>
                </template>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </template>
    </template>

    <!-- ============================================================
         NEXT AUCTION POOL
    ============================================================= -->
    <v-divider class="my-6" />

    <section>
      <div
        class="d-flex justify-space-between align-center flex-wrap ga-2 mb-3"
      >
        <div>
          <div class="text-h5 font-weight-bold">
            Next Auction Pool
          </div>

          <div class="text-body-2 text-medium-emphasis">
            This list grows automatically whenever an import batch expires.
          </div>
        </div>

        <v-chip
          v-if="collectingCycle"
          color="primary"
          variant="tonal"
          size="large"
        >
          {{ collectingCycle.batches_collected }}
          /
          {{ collectingCycle.batch_target }}
          imports
        </v-chip>
      </div>

      <v-card
        v-if="collectingCycle"
        variant="outlined"
        class="mb-3"
      >
        <v-card-text>
          <div
            class="d-flex justify-space-between text-body-2 mb-2"
          >
            <span>
              Import cycle progress
            </span>

            <strong>
              {{ collectingCycle.batches_collected }}
              /
              {{ collectingCycle.batch_target }}
            </strong>
          </div>

          <v-progress-linear
            height="10"
            rounded
            color="primary"
            :model-value="collectionProgress"
          />
        </v-card-text>
      </v-card>

      <v-card
        v-if="
          collectingCycle
          && collectingCycle.candidates.length > 0
        "
        variant="outlined"
      >
        <v-table>
          <thead>
            <tr>
              <th>
                <v-btn
                  variant="text"
                  size="small"
                  class="table-sort-button"
                  @click="toggleNextSort('name')"
                >
                  Tank

                  <v-icon
                    v-if="nextSortKey === 'name'"
                    end
                    size="small"
                  >
                    {{ nextSortIcon }}
                  </v-icon>
                </v-btn>
              </th>

              <th>
                <v-btn
                  variant="text"
                  size="small"
                  class="table-sort-button"
                  @click="toggleNextSort('br')"
                >
                  BR

                  <v-icon
                    v-if="nextSortKey === 'br'"
                    end
                    size="small"
                  >
                    {{ nextSortIcon }}
                  </v-icon>
                </v-btn>
              </th>

              <th>
                <v-btn
                  variant="text"
                  size="small"
                  class="table-sort-button"
                  @click="toggleNextSort('rank')"
                >
                  Rank

                  <v-icon
                    v-if="nextSortKey === 'rank'"
                    end
                    size="small"
                  >
                    {{ nextSortIcon }}
                  </v-icon>
                </v-btn>
              </th>

              <th>
                <v-btn
                  variant="text"
                  size="small"
                  class="table-sort-button"
                  @click="toggleNextSort('type')"
                >
                  Type

                  <v-icon
                    v-if="nextSortKey === 'type'"
                    end
                    size="small"
                  >
                    {{ nextSortIcon }}
                  </v-icon>
                </v-btn>
              </th>

              <th class="text-center">
                <v-btn
                  variant="text"
                  size="small"
                  class="table-sort-button"
                  @click="toggleNextSort('copies')"
                >
                  Copies

                  <v-icon
                    v-if="nextSortKey === 'copies'"
                    end
                    size="small"
                  >
                    {{ nextSortIcon }}
                  </v-icon>
                </v-btn>
              </th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="candidate in sortedCollectingCandidates"
              :key="candidate.id"
            >
              <td class="font-weight-bold">
                {{ candidate.tank.name }}
              </td>

              <td>
                {{ candidate.tank.battle_rating }}
              </td>

              <td>
                {{ candidate.tank.rank }}
              </td>

              <td>
                {{ candidate.tank.type }}
              </td>

              <td class="text-center">
                <v-chip
                  color="primary"
                  variant="tonal"
                  size="small"
                >
                  ×{{ candidate.quantity }}
                </v-chip>
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <v-alert
        v-else-if="collectingCycle"
        type="info"
        variant="tonal"
      >
        No unpurchased expired imports have entered the next auction
        pool yet.
      </v-alert>

      <v-alert
        v-else
        type="info"
        variant="tonal"
      >
        The next collecting cycle has not been created yet.
      </v-alert>
    </section>

    <!-- ============================================================
         SNACKBAR
    ============================================================= -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      timeout="4500"
    >
      {{ snackbar.text }}

      <template #actions>
        <v-btn
          variant="text"
          @click="snackbar.show = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import {
  computed,
  inject,
  onMounted,
  onUnmounted,
  reactive,
  ref,
} from "vue";

import { useUserStore } from "@/config/store.ts";
import { getAuthToken } from "@/config/api/user.ts";

/* ================================================================
   CONFIG
================================================================ */

const API_BASE = "/api/league";

/* ================================================================
   TYPES
================================================================ */

interface Tank {
  id: number;
  name: string;
  battle_rating: number;
  advanced_battle_rating?: number;
  evolved_battle_rating?: number;
  price: number;
  rank: number;
  type: string;
}

interface AuctionCandidateSource {
  id: number;
  source_import_id: number;
  import_available_from: string;
  import_available_until: string;
  import_discount: number;
  added_at: string;
}

interface AuctionCandidate {
  id: number;

  tank: Tank;

  quantity: number;

  vote_count: number;

  my_team_votes: number;
  max_team_votes_here: number;

  selected_quantity: number;

  sources: AuctionCandidateSource[];

  created_at: string;
}

interface AuctionImportBatch {
  id: number;

  available_from: string;
  expired_at: string;

  total_imports: number;
  leftover_imports: number;

  processed_at: string;
}

interface AuctionLot {
  id: number;

  position: number;

  candidate_id: number;
  source_import_id: number;

  tank: Tank;

  starting_bid: number;
  minimum_increment: number;

  current_bid: number | null;
  current_bidder: string | null;

  bid_count: number;
  minimum_next_bid: number | null;

  ends_at: string;
  last_bid_at: string | null;

  was_extended: boolean;

  winner: string | null;
  winning_bid: number | null;

  finalized_at: string | null;
}

type AuctionStatus =
  | "collecting"
  | "voting"
  | "scheduled"
  | "live"
  | "finished"
  | "cancelled";

interface AuctionCycle {
  id: number;

  status: AuctionStatus;

  batch_target: number;
  batches_collected: number;

  batch_progress: {
    current: number;
    target: number;
  };

  max_votes_per_team: number;

  my_votes_used: number;
  my_votes_remaining: number;

  lot_count: number | null;

  minimum_increment: number;

  voting_starts_at: string | null;
  voting_ends_at: string | null;

  auction_starts_at: string | null;
  auction_ends_at: string | null;

  import_batches: AuctionImportBatch[];

  candidates: AuctionCandidate[];
  lots: AuctionLot[];

  created_at: string;
  finished_at: string | null;
}

interface AuctionOverview {
  server_time: string;

  active_cycle: AuctionCycle | null;
  collecting_cycle: AuctionCycle | null;
}

interface Team {
  name: string;
  balance: number;
}

/* ================================================================
   VOTING SORT TYPES
================================================================ */

type VotingSort =
  | "votes-desc"
  | "votes-asc"
  | "name-asc"
  | "name-desc"
  | "copies-desc"
  | "copies-asc"
  | "br-desc"
  | "br-asc"
  | "rank-desc"
  | "rank-asc";

/* ================================================================
   NEXT AUCTION SORT TYPES
================================================================ */

type NextAuctionSortKey =
  | "name"
  | "br"
  | "rank"
  | "type"
  | "copies";

type SortDirection =
  | "asc"
  | "desc";

/* ================================================================
   STATE
================================================================ */

const userStore = useUserStore();

const overview = ref<AuctionOverview>({
  server_time: "",
  active_cycle: null,
  collecting_cycle: null,
});

const team = ref<Team>({
  name: "",
  balance: 0,
});

const loading = ref(false);
const loadError = ref("");

const currentTime = ref(Date.now());

const bidAmounts = reactive<Record<number, string>>({});

const bidLoadingLot = ref<number | null>(null);
const voteLoadingCandidate = ref<number | null>(null);

const snackbar = reactive({
  show: false,
  text: "",
  color: "success",
});

/* ================================================================
   VOTING FILTER / SORT STATE
================================================================ */

const votingSearch = ref("");

const votingTypeFilter =
  ref<string | null>(null);

const votingRankFilter =
  ref<number | null>(null);

const onlyMyVotes = ref(false);

const votingSort =
  ref<VotingSort>("votes-desc");

const votingSortOptions = [
  {
    title: "Votes: highest first",
    value: "votes-desc",
  },
  {
    title: "Votes: lowest first",
    value: "votes-asc",
  },
  {
    title: "Tank name: A → Z",
    value: "name-asc",
  },
  {
    title: "Tank name: Z → A",
    value: "name-desc",
  },
  {
    title: "Copies: most first",
    value: "copies-desc",
  },
  {
    title: "Copies: least first",
    value: "copies-asc",
  },
  {
    title: "Battle Rating: highest first",
    value: "br-desc",
  },
  {
    title: "Battle Rating: lowest first",
    value: "br-asc",
  },
  {
    title: "Rank: highest first",
    value: "rank-desc",
  },
  {
    title: "Rank: lowest first",
    value: "rank-asc",
  },
];

/* ================================================================
   NEXT AUCTION TABLE SORT STATE
================================================================ */

const nextSortKey =
  ref<NextAuctionSortKey>("name");

const nextSortDirection =
  ref<SortDirection>("asc");

/* ================================================================
   COOKIES / AUTH
================================================================ */

const $cookies = inject<any>("$cookies");

const csrfToken =
  $cookies?.get("csrftoken") ?? "";

function authenticatedHeaders(
  includeJson = false
): HeadersInit {
  const headers: Record<string, string> = {};

  const token = getAuthToken();

  if (token) {
    headers["Authorization"] = token;
  }

  if (includeJson) {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = csrfToken;
  }

  return headers;
}

/* ================================================================
   BASIC COMPUTEDS
================================================================ */

const activeCycle = computed(
  () => overview.value.active_cycle
);

const collectingCycle = computed(
  () => overview.value.collecting_cycle
);

const isCommander = computed(() => {
  return (
    userStore.groups.some(
      group => group.name === "commander"
    )
    ||
    userStore.groups.some(
      group => group.name === "admin"
    )
  );
});

const collectionProgress = computed(() => {
  if (!collectingCycle.value) {
    return 0;
  }

  if (collectingCycle.value.batch_target <= 0) {
    return 0;
  }

  return Math.min(
    100,
    (
      collectingCycle.value.batches_collected
      /
      collectingCycle.value.batch_target
    ) * 100
  );
});

/* ================================================================
   VOTING FILTERS / SORTING
================================================================ */

const votingTankTypes = computed(() => {
  if (!activeCycle.value) {
    return [];
  }

  return Array.from(
    new Set(
      activeCycle.value.candidates
        .map(candidate => candidate.tank.type)
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));
});

const votingRanks = computed(() => {
  if (!activeCycle.value) {
    return [];
  }

  return Array.from(
    new Set(
      activeCycle.value.candidates
        .map(candidate => candidate.tank.rank)
    )
  ).sort((a, b) => a - b);
});

const hasVotingFilters = computed(() => {
  return (
    !!votingSearch.value
    || votingTypeFilter.value !== null
    || votingRankFilter.value !== null
    || onlyMyVotes.value
  );
});

function clearVotingFilters() {
  votingSearch.value = "";
  votingTypeFilter.value = null;
  votingRankFilter.value = null;
  onlyMyVotes.value = false;
}

const filteredVotingCandidates = computed(() => {
  if (!activeCycle.value) {
    return [];
  }

  const search =
    votingSearch.value
      .trim()
      .toLowerCase();

  const candidates =
    activeCycle.value.candidates.filter(
      candidate => {
        if (
          search
          && !candidate.tank.name
            .toLowerCase()
            .includes(search)
        ) {
          return false;
        }

        if (
          votingTypeFilter.value !== null
          && candidate.tank.type !== votingTypeFilter.value
        ) {
          return false;
        }

        if (
          votingRankFilter.value !== null
          && candidate.tank.rank !== votingRankFilter.value
        ) {
          return false;
        }

        if (
          onlyMyVotes.value
          && candidate.my_team_votes <= 0
        ) {
          return false;
        }

        return true;
      }
    );

  return [...candidates].sort(
    (a, b) => {
      switch (votingSort.value) {
        case "votes-asc":
          return (
            a.vote_count - b.vote_count
            || a.tank.name.localeCompare(
              b.tank.name
            )
          );

        case "votes-desc":
          return (
            b.vote_count - a.vote_count
            || a.tank.name.localeCompare(
              b.tank.name
            )
          );

        case "name-desc":
          return b.tank.name.localeCompare(
            a.tank.name
          );

        case "name-asc":
          return a.tank.name.localeCompare(
            b.tank.name
          );

        case "copies-desc":
          return (
            b.quantity - a.quantity
            || a.tank.name.localeCompare(
              b.tank.name
            )
          );

        case "copies-asc":
          return (
            a.quantity - b.quantity
            || a.tank.name.localeCompare(
              b.tank.name
            )
          );

        case "br-desc":
          return (
            b.tank.battle_rating
            - a.tank.battle_rating
            || a.tank.name.localeCompare(
              b.tank.name
            )
          );

        case "br-asc":
          return (
            a.tank.battle_rating
            - b.tank.battle_rating
            || a.tank.name.localeCompare(
              b.tank.name
            )
          );

        case "rank-desc":
          return (
            b.tank.rank - a.tank.rank
            || a.tank.name.localeCompare(
              b.tank.name
            )
          );

        case "rank-asc":
          return (
            a.tank.rank - b.tank.rank
            || a.tank.name.localeCompare(
              b.tank.name
            )
          );

        default:
          return 0;
      }
    }
  );
});

/* ================================================================
   NEXT AUCTION SORTING
================================================================ */

const nextSortIcon = computed(() => {
  return nextSortDirection.value === "asc"
    ? "mdi-arrow-up"
    : "mdi-arrow-down";
});

function toggleNextSort(
  key: NextAuctionSortKey
) {
  if (nextSortKey.value === key) {
    nextSortDirection.value =
      nextSortDirection.value === "asc"
        ? "desc"
        : "asc";

    return;
  }

  nextSortKey.value = key;

  if (
    key === "br"
    || key === "rank"
    || key === "copies"
  ) {
    nextSortDirection.value = "desc";
  } else {
    nextSortDirection.value = "asc";
  }
}

const sortedCollectingCandidates =
  computed(() => {
    if (!collectingCycle.value) {
      return [];
    }

    const direction =
      nextSortDirection.value === "asc"
        ? 1
        : -1;

    return [
      ...collectingCycle.value.candidates
    ].sort((a, b) => {
      let comparison = 0;

      switch (nextSortKey.value) {
        case "name":
          comparison =
            a.tank.name.localeCompare(
              b.tank.name
            );
          break;

        case "br":
          comparison =
            a.tank.battle_rating
            - b.tank.battle_rating;
          break;

        case "rank":
          comparison =
            a.tank.rank
            - b.tank.rank;
          break;

        case "type":
          comparison =
            a.tank.type.localeCompare(
              b.tank.type
            );
          break;

        case "copies":
          comparison =
            a.quantity - b.quantity;
          break;
      }

      if (comparison === 0) {
        comparison =
          a.tank.name.localeCompare(
            b.tank.name
          );
      }

      return comparison * direction;
    });
  });

/* ================================================================
   FORMATTERS
================================================================ */

function formatMoney(
  value: number | null | undefined
): string {
  const amount = Number(value ?? 0);

  return (
    new Intl.NumberFormat(undefined, {
      maximumFractionDigits: 0,
    }).format(amount)
    + " $"
  );
}

function formatDateTime(
  iso: string | null | undefined
): string {
  if (!iso) {
    return "—";
  }

  const date = new Date(iso);

  return new Intl.DateTimeFormat(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }
  ).format(date);
}

function formatTime(
  iso: string | null | undefined
): string {
  if (!iso) {
    return "—";
  }

  return new Intl.DateTimeFormat(
    undefined,
    {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }
  ).format(
    new Date(iso)
  );
}

function statusLabel(
  status: AuctionStatus
): string {
  const labels: Record<AuctionStatus, string> = {
    collecting: "Collecting",
    voting: "Voting",
    scheduled: "Scheduled",
    live: "Live",
    finished: "Finished",
    cancelled: "Cancelled",
  };

  return labels[status];
}

function statusColor(
  status: AuctionStatus
): string {
  const colors: Record<AuctionStatus, string> = {
    collecting: "primary",
    voting: "info",
    scheduled: "warning",
    live: "success",
    finished: "grey",
    cancelled: "error",
  };

  return colors[status];
}

/* ================================================================
   TIME HELPERS
================================================================ */

function millisecondsUntil(
  iso: string | null | undefined
): number {
  if (!iso) {
    return 0;
  }

  return Math.max(
    0,
    new Date(iso).getTime()
      - currentTime.value
  );
}

function countdown(
  iso: string | null | undefined
): string {
  if (!iso) {
    return "—";
  }

  const milliseconds =
    millisecondsUntil(iso);

  if (milliseconds <= 0) {
    return "00:00";
  }

  const totalSeconds =
    Math.floor(milliseconds / 1000);

  const days =
    Math.floor(totalSeconds / 86400);

  const hours =
    Math.floor(
      (totalSeconds % 86400) / 3600
    );

  const minutes =
    Math.floor(
      (totalSeconds % 3600) / 60
    );

  const seconds =
    totalSeconds % 60;

  if (days > 0) {
    return (
      `${days}d `
      + `${String(hours).padStart(2, "0")}:`
      + `${String(minutes).padStart(2, "0")}:`
      + `${String(seconds).padStart(2, "0")}`
    );
  }

  return (
    `${String(hours).padStart(2, "0")}:`
    + `${String(minutes).padStart(2, "0")}:`
    + `${String(seconds).padStart(2, "0")}`
  );
}

function shortCountdown(
  iso: string | null | undefined
): string {
  if (!iso) {
    return "00:00";
  }

  const milliseconds =
    millisecondsUntil(iso);

  const totalSeconds =
    Math.max(
      0,
      Math.floor(milliseconds / 1000)
    );

  const hours =
    Math.floor(totalSeconds / 3600);

  const minutes =
    Math.floor(
      (totalSeconds % 3600) / 60
    );

  const seconds =
    totalSeconds % 60;

  if (hours > 0) {
    return (
      `${String(hours).padStart(2, "0")}:`
      + `${String(minutes).padStart(2, "0")}:`
      + `${String(seconds).padStart(2, "0")}`
    );
  }

  return (
    `${String(minutes).padStart(2, "0")}:`
    + `${String(seconds).padStart(2, "0")}`
  );
}

/* ================================================================
   AUCTION STATE HELPERS
================================================================ */

function isEffectivelyLive(
  cycle: AuctionCycle
): boolean {
  if (
    cycle.status === "finished"
    || cycle.status === "cancelled"
  ) {
    return false;
  }

  if (!cycle.auction_starts_at) {
    return false;
  }

  if (
    currentTime.value
    < new Date(
      cycle.auction_starts_at
    ).getTime()
  ) {
    return false;
  }

  /*
   * Do not compare against cycle.auction_ends_at here.
   *
   * Individual lots can remain open because of
   * their anti-snipe extensions.
   */
  return cycle.lots.some(
    lot => !lot.finalized_at
  );
}

function isLotClosed(
  lot: AuctionLot
): boolean {
  if (lot.finalized_at) {
    return true;
  }

  return (
    currentTime.value
    >= new Date(lot.ends_at).getTime()
  );
}

function isMyTeamLeading(
  lot: AuctionLot
): boolean {
  return (
    !!team.value.name
    && lot.current_bidder === team.value.name
  );
}

function voteProgress(
  cycle: AuctionCycle
): number {
  if (cycle.max_votes_per_team <= 0) {
    return 0;
  }

  return Math.min(
    100,
    (
      cycle.my_votes_used
      /
      cycle.max_votes_per_team
    ) * 100
  );
}

/* ================================================================
   FETCH
================================================================ */

async function fetchAuctionOverview(
  silent = false
) {
  if (!silent) {
    loading.value = true;
  }

  try {
    const response = await fetch(
      `${API_BASE}/auctions/`,
      {
        headers: authenticatedHeaders(),
        credentials: "same-origin",
      }
    );

    if (!response.ok) {
      throw new Error(
        `Failed to load auctions (${response.status}).`
      );
    }

    overview.value =
      await response.json();

    normalizeBidInputs();

    loadError.value = "";

  } catch (error: any) {
    console.error(
      "Failed to fetch auctions:",
      error
    );

    loadError.value =
      error?.message
      ?? "Failed to load auctions.";

  } finally {
    if (!silent) {
      loading.value = false;
    }
  }
}

async function fetchTeamDetails() {
  if (!userStore.team) {
    return;
  }

  try {
    const response = await fetch(
      `${API_BASE}/teams/${encodeURIComponent(userStore.team)}/`,
      {
        headers: authenticatedHeaders(),
        credentials: "same-origin",
      }
    );

    if (!response.ok) {
      throw new Error(
        "Failed to load team details."
      );
    }

    team.value =
      await response.json();

  } catch (error) {
    console.error(
      "Failed to fetch team:",
      error
    );
  }
}

async function refreshEverything() {
  await Promise.all([
    fetchAuctionOverview(),
    fetchTeamDetails(),
  ]);
}

/* ================================================================
   VOTING
================================================================ */

async function addCandidateVote(
  candidate: AuctionCandidate
) {
  if (
    !activeCycle.value
    || voteLoadingCandidate.value !== null
  ) {
    return;
  }

  voteLoadingCandidate.value =
    candidate.id;

  try {
    const response = await fetch(
      `${API_BASE}/auctions/${activeCycle.value.id}/candidates/${candidate.id}/vote/`,
      {
        method: "POST",

        headers:
          authenticatedHeaders(true),

        credentials: "same-origin",

        body: JSON.stringify({}),
      }
    );

    const data =
      await safeJson(response);

    if (!response.ok) {
      throw new Error(
        extractError(
          data,
          "Failed to add vote."
        )
      );
    }

    showMessage(
      `Vote added to ${candidate.tank.name}.`,
      "success"
    );

    await fetchAuctionOverview(true);

  } catch (error: any) {
    showMessage(
      error?.message
      ?? "Failed to vote.",
      "error"
    );

  } finally {
    voteLoadingCandidate.value = null;
  }
}

async function removeCandidateVote(
  candidate: AuctionCandidate
) {
  if (
    !activeCycle.value
    || voteLoadingCandidate.value !== null
  ) {
    return;
  }

  voteLoadingCandidate.value =
    candidate.id;

  try {
    const response = await fetch(
      `${API_BASE}/auctions/${activeCycle.value.id}/candidates/${candidate.id}/vote/`,
      {
        method: "DELETE",

        headers:
          authenticatedHeaders(true),

        credentials: "same-origin",
      }
    );

    if (!response.ok) {
      const data =
        await safeJson(response);

      throw new Error(
        extractError(
          data,
          "Failed to remove vote."
        )
      );
    }

    showMessage(
      `Vote removed from ${candidate.tank.name}.`,
      "success"
    );

    await fetchAuctionOverview(true);

  } catch (error: any) {
    showMessage(
      error?.message
      ?? "Failed to remove vote.",
      "error"
    );

  } finally {
    voteLoadingCandidate.value = null;
  }
}

/* ================================================================
   BIDDING
================================================================ */

function normalizeBidInputs() {
  const cycle =
    overview.value.active_cycle;

  if (!cycle) {
    return;
  }

  for (const lot of cycle.lots) {
    if (isLotClosed(lot)) {
      continue;
    }

    const minimum =
      lot.minimum_next_bid
      ?? lot.starting_bid;

    const currentInput =
      Number(bidAmounts[lot.id]);

    if (
      !bidAmounts[lot.id]
      || !Number.isFinite(currentInput)
      || currentInput < minimum
    ) {
      bidAmounts[lot.id] =
        String(minimum);
    }
  }
}

function requiredFundsForBid(
  lot: AuctionLot,
  amount: number
): number {
  /*
   * When our team already leads the lot, only the
   * increase over our existing held bid is required.
   */
  if (
    isMyTeamLeading(lot)
    && lot.current_bid !== null
  ) {
    return Math.max(
      0,
      amount - lot.current_bid
    );
  }

  return amount;
}

function canSubmitBid(
  lot: AuctionLot
): boolean {
  if (!isCommander.value) {
    return false;
  }

  if (isLotClosed(lot)) {
    return false;
  }

  const amount =
    Number(bidAmounts[lot.id]);

  if (
    !Number.isFinite(amount)
    || amount <= 0
  ) {
    return false;
  }

  const minimum =
    lot.minimum_next_bid
    ?? lot.starting_bid;

  if (amount < minimum) {
    return false;
  }

  const required =
    requiredFundsForBid(
      lot,
      amount
    );

  return (
    required <= team.value.balance
  );
}

async function submitBid(
  lot: AuctionLot
) {
  if (
    !canSubmitBid(lot)
    || bidLoadingLot.value !== null
  ) {
    return;
  }

  const amount =
    Number(bidAmounts[lot.id]);

  bidLoadingLot.value =
    lot.id;

  try {
    const response = await fetch(
      `${API_BASE}/auctions/lots/${lot.id}/bid/`,
      {
        method: "POST",

        headers:
          authenticatedHeaders(true),

        credentials: "same-origin",

        body: JSON.stringify({
          amount,
        }),
      }
    );

    const data =
      await safeJson(response);

    if (!response.ok) {
      throw new Error(
        extractError(
          data,
          "Bid failed."
        )
      );
    }

    showMessage(
      `Bid of ${formatMoney(amount)} placed on ${lot.tank.name}.`,
      "success"
    );

    await Promise.all([
      fetchAuctionOverview(true),
      fetchTeamDetails(),
    ]);

  } catch (error: any) {
    showMessage(
      error?.message
      ?? "Bid failed.",
      "error"
    );

    /*
     * Server is authoritative. Refresh even after a
     * rejected bid in case somebody beat us to it.
     */
    await Promise.all([
      fetchAuctionOverview(true),
      fetchTeamDetails(),
    ]);

  } finally {
    bidLoadingLot.value = null;
  }
}

/* ================================================================
   ERROR / SNACKBAR HELPERS
================================================================ */

async function safeJson(
  response: Response
): Promise<any> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function extractError(
  data: any,
  fallback: string
): string {
  if (!data) {
    return fallback;
  }

  /*
   * DRF ValidationError("message") may be returned
   * as a root-level array.
   */
  if (Array.isArray(data)) {
    return data
      .map(value => String(value))
      .join(" ");
  }

  if (typeof data === "string") {
    return data;
  }

  if (typeof data.error === "string") {
    return data.error;
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((value: any) => String(value))
      .join(" ");
  }

  if (
    data.detail
    && typeof data.detail === "object"
  ) {
    return Object.values(data.detail)
      .flat()
      .map(value => String(value))
      .join(" ");
  }

  /*
   * Some serializer validation errors come back as:
   *
   * {
   *   amount: ["..."]
   * }
   */
  if (typeof data === "object") {
    const messages = Object.values(data)
      .flat()
      .map(value => String(value));

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  return fallback;
}

function showMessage(
  text: string,
  color: string
) {
  snackbar.text = text;
  snackbar.color = color;
  snackbar.show = true;
}

/* ================================================================
   POLLING
================================================================ */

let clockTimer:
  ReturnType<typeof setInterval>
  | null = null;

let pollingTimer:
  ReturnType<typeof setTimeout>
  | null = null;

let stopped = false;

function shouldUseFastPolling(): boolean {
  const cycle =
    activeCycle.value;

  if (!cycle) {
    return false;
  }

  return isEffectivelyLive(cycle);
}

function scheduleNextPoll() {
  if (stopped) {
    return;
  }

  if (pollingTimer) {
    clearTimeout(pollingTimer);
  }

  /*
   * Live auction:
   *     2.5 seconds
   *
   * Voting / scheduled / collecting:
   *     15 seconds
   */
  const delay =
    shouldUseFastPolling()
      ? 2500
      : 15000;

  pollingTimer =
    setTimeout(async () => {
      if (shouldUseFastPolling()) {
        /*
         * Refresh team during bidding too because our
         * balance can increase asynchronously if another
         * team outbids us.
         */
        await Promise.all([
          fetchAuctionOverview(true),
          fetchTeamDetails(),
        ]);
      } else {
        await fetchAuctionOverview(true);
      }

      scheduleNextPoll();

    }, delay);
}

/* ================================================================
   LIFECYCLE
================================================================ */

onMounted(async () => {
  stopped = false;

  clockTimer =
    setInterval(() => {
      currentTime.value =
        Date.now();
    }, 500);

  await refreshEverything();

  scheduleNextPoll();
});

onUnmounted(() => {
  stopped = true;

  if (clockTimer) {
    clearInterval(clockTimer);
  }

  if (pollingTimer) {
    clearTimeout(pollingTimer);
  }
});
</script>

<style scoped>
.auction-page {
  max-width: 1800px;
}

/* Tank our school has allocated votes to. */
.selected-candidate {
  border: 1px solid
    rgb(var(--v-theme-primary));
}

/* Lot currently led by our team. */
.leading-lot {
  border: 2px solid
    rgb(var(--v-theme-success));
}

/* Finished/expired lot appearance. */
.closed-lot {
  opacity: 0.82;
}

/* Countdown surface compatible with light/dark themes. */
.timer-box {
  background:
    rgba(
      var(--v-theme-on-surface),
      0.05
    );
}

.vote-number {
  min-width: 32px;
  text-align: center;
}

.lot-card {
  transition:
    border-color 0.15s ease,
    opacity 0.15s ease;
}

.v-table td,
.v-table th {
  padding: 10px 12px;
}

/* Clickable table sorting headings. */
.table-sort-button {
  min-width: 0;
  padding-left: 0;
  padding-right: 0;

  text-transform: none;
  font-weight: 700;
  letter-spacing: normal;
}

@media (max-width: 600px) {
  .auction-page {
    padding-left: 8px !important;
    padding-right: 8px !important;
  }
}
</style>