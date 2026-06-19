export interface HealthResponse {
  status: string;
}

export interface CircuitInfo {
  circuit_id: string;
  default_race_length: number;
}

export interface CircuitsResponse {
  circuits: CircuitInfo[];
  eras: string[];
}

export interface StrategySelection {
  circuit_id: string;
  era: string;
  race_length: number;
}

export interface StrategyRequest {
  circuit_id: string;
  era: string;
  race_length: number;
  n_scenarios?: number;
  seed?: number;
}

export interface StrategyResponse {
  status: string;
  compounds: string[];
  stint_lengths: number[];
  pit_laps: number[];
  expected_cost_seconds: number;
  pit_loss_seconds: number;
}

export interface CompareRequest {
  circuit_id: string;
  era: string;
  race_length: number;
  n_scenarios?: number;
  seed?: number;
}

export interface PlanSummary {
  status: string;
  compounds: string[];
  stint_lengths: number[];
  pit_laps: number[];
  expected_cost_seconds: number;
}

export interface CompareResponse {
  deterministic: PlanSummary;
  stochastic: PlanSummary;
  deterministic_costs: number[];
  stochastic_costs: number[];
  gap_seconds: number;
  gap_standard_error: number;
  gap_is_significant: boolean;
  pit_loss_seconds: number;
}

export interface EvaluationSummaryResponse {
  driver_races: number;
  mean_actual_regret_seconds: number;
  median_actual_regret_seconds: number;
  mean_policy_regret_seconds: number;
  median_policy_regret_seconds: number;
  captured_fraction: number;
  mean_regret_positions_per_race: number | null;
}
