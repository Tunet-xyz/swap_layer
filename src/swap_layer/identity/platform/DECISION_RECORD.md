# Identity Platform Strategy: The "Bootstrapper's Choice"

**Date:** December 26, 2025
**Decision:** Adopt **WorkOS** as the primary Identity Provider (IdP).
**Architecture:** Vendor-Agnostic Abstraction Layer (Adapter Pattern).

---

## 1. The Strategic Context

We are building `CodedX`, a developer platform targeting:
1.  **Academia:** 1 Million+ Free Users (Students/Researchers).
2.  **Enterprise:** High-value B2B contracts (SSO/SAML required).
3.  **Geography:** UK/EU focus (GDPR/Data Sovereignty sensitivity).

### The Core Conflict
*   **Volume vs. Cost:** We need to support 1M free users without going bankrupt.
*   **Sovereignty vs. Convenience:** We prefer UK hosting, but US-hosted solutions are cheaper/better.
*   **Vendor Risk:** We fear "Vendor Lock-in" (e.g., price hikes, acquisition, shutdown).

---

## 2. The Decision Matrix (Weighted)

We evaluated 5 options against 13 criteria. **WorkOS** won by a significant margin for our specific business model.

| Criteria | Weight | **WorkOS** | **Supabase (SaaS)** | **Supabase (Self-Hosted)** | **Auth0** | **Firebase** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Free Tier Volume** | **x3** | **5** (1M Free) | **2** (50k Limit) | **5** (Unlimited*) | **1** | **5** |
| **2. Scale Cost** | **x3** | **5** (Free B2C) | **1** ($3k/mo) | **5** (Cheap Infra) | **1** | **4** |
| **3. Data Residency** | **x3** | **1** (US Only) | **5** (London) | **5** (Anywhere) | **5** | **2** |
| **4. Enterprise SSO** | **x2** | **5** (Portal) | **3** (DIY UI) | **2** (Harder DIY) | **5** | **2** |
| **5. Vendor Lock-in** | **x2** | **2** (High) | **4** (Low) | **5** (Zero) | **1** | **1** |
| **6. B2B Multi-Tenancy** | **x2** | **5** (Native) | **2** (RLS Pain) | **2** (RLS Pain) | **5** | **1** |
| **TOTAL SCORE** | | **87** | **70** | **86** | **73** | **65** |

### Why WorkOS Won (Score: 87)
1.  **Financial Survival:** The "1 Million MAU Free Tier" is the only way to support the Academia strategy without raising VC funding.
2.  **Enterprise Readiness:** The "Admin Portal" for SSO allows us to sell to Enterprises immediately without building complex SAML UI.
3.  **Developer Focus:** It is built for B2B SaaS, unlike Firebase (B2C mobile) or Keycloak (IT Ops).

### Why Others Lost
*   **Auth0:** The "Year 2 Cliff". The Startup Plan (100k users) expires after 1 year, leading to a massive bill.
*   **Supabase (SaaS):** The "Success Tax". 1M free users would cost ~$37,000/year in overage fees.
*   **Supabase (Self-Hosted):** The "Time Tax". It scored 86 (very close), but requires 10-20 hours/month of DevOps maintenance. As a solo founder, Time > Money.

---

## 3. The "Data Residency" Risk & Mitigation

**The Risk:** WorkOS hosts data in the US.
*   **Impact:** Most users (Devs/Students) do not care. However, strict UK Gov/NHS contracts might require UK hosting.
*   **Legal Status:** GDPR Compliant via Standard Contractual Clauses (SCCs) and Data Privacy Framework (DPF).

**The Mitigation: The Abstraction Layer**
We have implemented a `UserIdentity` model and `AuthProviderAdapter` interface.
*   **Decoupling:** Our database does *not* rely on WorkOS IDs as primary keys.
*   **Migration Path:** If a major contract requires UK hosting, we can swap the Adapter to **Self-Hosted Supabase** (running in London) without rewriting the application.
*   **Strategy:** "Launch with WorkOS (Speed/Cost), Migrate if Revenue Demands it."

---

## 4. Implementation Details

### The Abstraction Layer
*   **Model:** `services.authentication.models.UserIdentity`
*   **Adapter:** `services.authentication.adapter.AuthProviderAdapter`
*   **Implementation:** `swap_layer.identity.workos.adapter.WorkOSAdapter`

### Key Configuration
*   **SDK:** `workos-python`
*   **Auth Flow:** AuthKit (Hosted Login)
*   **Session:** Sealed Sessions (Encrypted Cookies)

---

## 5. Future Triggers (When to Change)

We will re-evaluate this decision if:
1.  **Revenue > $20k/MRR:** We can afford to pay for Supabase Enterprise or hire a DevOps engineer for Self-Hosting.
2.  **Hard Requirement:** A signed contract >$50k/year explicitly mandates UK Data Residency.
3.  **Acquisition:** WorkOS is acquired by a hostile vendor (e.g., Oracle).
