// Aftercare is one backend serving multiple independent brands (ArcticAir,
// AquaSpin, ...). A brand's own staff dashboard must only ever see that
// brand's tickets and registrations -- never another brand's. This is
// enforced here, by Cedar, not by an `if` buried in a route handler.
//
// principal = Staff::"<brand>"   -- who is logged in (the simulated
//                                   "which brand's staff am I" picker)
// action    = Action::"viewDashboard"
// resource  = Brand::"<brand>"   -- whose dashboard data is being requested
permit(
    principal,
    action == Action::"viewDashboard",
    resource
) when {
    principal.brand == resource.brand
};
