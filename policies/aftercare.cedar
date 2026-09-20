// Aftercare authorization. One backend, several independent brands: a brand's staff
// must only ever see that brand's data. Enforced here, by Cedar, not by an `if` in a
// route handler. Every policy has an @id so a decision can say *which rule* decided it.
//
//   principal = Staff::"<username>"  { brand, role }   -- who the *server* says is signed in
//   resource  = Brand::"<brand>"     { brand }         -- a dashboard
//             | Ticket::"<id>"       { brand, safety } -- one ticket
// Schema: aftercare.cedarschema (checked by `cedar validate` in tests).

@id("same-brand-views-dashboard")
permit (principal, action == Action::"viewDashboard", resource is Brand)
when { principal.brand == resource.brand };

@id("same-brand-views-ticket")
permit (principal, action == Action::"viewTicket", resource is Ticket)
when { principal.brand == resource.brand };

// Any staff member may read tickets; only a manager may change what state one is in.
@id("managers-update-ticket-status")
permit (principal, action == Action::"updateTicketStatus", resource is Ticket)
when { principal.brand == resource.brand && principal.role == "manager" };

// Customer phone numbers are masked by default. A safety ticket may need a same-day
// call to the customer, so for those (and only those) the number is shown in full.
@id("safety-tickets-show-phone")
permit (principal, action == Action::"viewPhoneUnmasked", resource is Ticket)
when { principal.brand == resource.brand && resource.safety == true };

// Belt and braces: a forbid always beats a permit, so no future permit can leak across brands.
@id("no-cross-brand")
forbid (principal, action, resource)
when { principal.brand != resource.brand };
