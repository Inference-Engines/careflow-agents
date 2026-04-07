const BASE_URL = '';
const PATIENT_ID = '11111111-1111-1111-1111-111111111111';

// ── Types ────────────────────────────────────────────────────────────────────

export interface MetricLatest {
    value: string;
    unit: string;
    status: string;
    recorded_at: string;
    [key: string]: unknown;
}

export interface MetricTrendPoint {
    day: number;
    value: number;
    recorded_at: string;
    [key: string]: unknown;
}

export interface Medication {
    id: string;
    name: string;
    dose: string;
    schedule: string;
    taken_today: boolean;
    [key: string]: unknown;
}

export interface Appointment {
    id: string;
    title: string;
    date: string;
    time: string;
    doctor: string;
    location: string;
    status: string;
    type: string;
    note?: string;
    [key: string]: unknown;
}

export interface Visit {
    id: string;
    date: string;
    location: string;
    summary: string;
    extractions: unknown[];
    [key: string]: unknown;
}

export interface Caregiver {
    name: string;
    relation: string;
    contact: string;
    [key: string]: unknown;
}

// ── Fetch helpers ────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string): Promise<T | null> {
    try {
        const res = await fetch(`${BASE_URL}${path}`);
        if (!res.ok) return null;
        const json = await res.json();
        // server.py wraps responses in { data: ..., source: ... }
        // Unwrap the data field if present
        if (json && typeof json === 'object' && 'data' in json) {
            return json.data as T;
        }
        return json as T;
    } catch {
        return null;
    }
}

async function apiFetchArray<T>(path: string): Promise<T[]> {
    try {
        const res = await fetch(`${BASE_URL}${path}`);
        if (!res.ok) return [];
        const json = await res.json();
        // Unwrap { data: [...], source: ... } wrapper
        const data = json && typeof json === 'object' && 'data' in json ? json.data : json;
        return Array.isArray(data) ? (data as T[]) : [];
    } catch {
        return [];
    }
}

// ── Public API functions ─────────────────────────────────────────────────────

export async function fetchLatestMetric(type: string): Promise<MetricLatest | null> {
    return apiFetch<MetricLatest>(
        `/api/metrics/latest?patient_id=${PATIENT_ID}&type=${encodeURIComponent(type)}`,
    );
}

export async function fetchMetricTrend(type: string, days = 90): Promise<MetricTrendPoint[]> {
    return apiFetchArray<MetricTrendPoint>(
        `/api/metrics/trend?patient_id=${PATIENT_ID}&type=${encodeURIComponent(type)}&days=${days}`,
    );
}

export async function fetchActiveMedications(): Promise<Medication[]> {
    return apiFetchArray<Medication>(
        `/api/medications/active?patient_id=${PATIENT_ID}`,
    );
}

export async function markMedicationTaken(medId: string): Promise<boolean> {
    try {
        const res = await fetch(`${BASE_URL}/api/medications/${medId}/mark-taken?patient_id=${PATIENT_ID}`, {
            method: 'POST',
        });
        return res.ok;
    } catch {
        return false;
    }
}

export async function fetchAppointments(): Promise<Appointment[]> {
    return apiFetchArray<Appointment>(
        `/api/appointments?patient_id=${PATIENT_ID}`,
    );
}

export async function fetchRecentVisits(limit = 5): Promise<Visit[]> {
    return apiFetchArray<Visit>(
        `/api/visits/recent?patient_id=${PATIENT_ID}&limit=${limit}`,
    );
}

export async function fetchCaregiver(): Promise<Caregiver | null> {
    return apiFetch<Caregiver>(
        `/api/caregiver?patient_id=${PATIENT_ID}`,
    );
}
