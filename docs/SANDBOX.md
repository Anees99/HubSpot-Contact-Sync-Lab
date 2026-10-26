# Practical demonstration checklist

1. Create test contacts in a developer/test account with no real customer data.
2. Define `portfolio_external_id` as a unique contact property; reconcile existing IDs.
3. Prepare a field-mapping sheet and verify empty-field behavior.
4. Run the sample CSV and explain why conflicting identities are quarantined.
5. Review the proposed request body before any write.
6. If building a live adapter, use a private-app token with necessary contact scopes,
   keep secrets out of source, log record IDs rather than raw personal data, and apply
   bounded transient retries. Verify rate limits for the account.
7. Test one create and one update, partial failure, expired credentials, and replay.
8. Compare returned properties against the expected external IDs before recording success.
9. Show contact properties and workflow enrollment in the HubSpot UI; document what
   was tested with screenshots that contain only synthetic records.

The first eight software-planning concepts can be demonstrated locally. Native UI,
workflow enrollment and live account tests remain to be done. No HubSpot certification
or production experience is implied.
