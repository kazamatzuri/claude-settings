# Common Bevy Pitfalls Reference

## 1. Event System Usage

**❌ Problem:**
Using old-style event readers/writers instead of observers.

**✅ Solution:**
Use the observer pattern:
```rust
#[derive(Event, Clone)]  // Must derive Clone!
struct MyEvent { data: String }

// Register observer
app.add_observer(handle_event);

// Handler with Trigger
fn handle_event(
    trigger: Trigger<MyEvent>,
    // ... other params
) {
    let event = trigger.event();
}

// Trigger through commands
fn trigger_event(mut commands: Commands) {
    commands.trigger(MyEvent { data: "test".into() });
}
```

See `references/bevy_specific_tips.md` for complete event patterns.

## 2. Querying Material Handles

**❌ Problem:**
```rust
// Materials are not directly queryable
Query<&Handle<StandardMaterial>>
```

**✅ Solution:**
Use the `MeshMaterial3d` wrapper:
```rust
Query<&MeshMaterial3d<StandardMaterial>>

// Access handle with .0
for material_3d in query.iter() {
    if let Some(material) = materials.get_mut(&material_3d.0) {
        material.emissive = color;
    }
}
```

## 3. Forgetting to Register Systems

**❌ Problem:**
```rust
// Created system but forgot to add to app
pub fn my_new_system() { /* ... */ }
```

**✅ Solution:**
Always add to `main.rs`:
```rust
.add_systems(Update, my_new_system)
```

## 4. Borrowing Conflicts

**❌ Problem:**
```rust
// Can't have multiple mutable borrows
mut query1: Query<&mut Transform>,
mut query2: Query<&mut Transform>,  // Error!
```

**✅ Solution:**
```rust
// Use get_many_mut for specific entities
mut query: Query<&mut Transform>,

if let Ok([mut a, mut b]) = query.get_many_mut([entity_a, entity_b]) {
    // Can mutate both
}
```

## 5. Not Using Changed<T>

**❌ Problem:**
```rust
// Runs every frame for every entity
fn system(query: Query<&BigFive>) {
    for traits in query.iter() {
        // Expensive calculation every frame
    }
}
```

**✅ Solution:**
```rust
// Only runs when BigFive changes
fn system(query: Query<&BigFive, Changed<BigFive>>) {
    for traits in query.iter() {
        // Only when needed
    }
}
```

## 6. Entity Queries After Despawn

**❌ Problem:**
```rust
commands.entity(entity).despawn();
// Later in same system
let component = query.get(entity).unwrap();  // Crash!
```

**✅ Solution:**
Commands apply at end of stage. Use `Ok()` pattern:
```rust
if let Ok(component) = query.get(entity) {
    // Safe
}
```

## 7. Material/Asset Handle Confusion

**❌ Problem:**
```rust
// Created material but didn't store handle
materials.add(StandardMaterial { .. });  // Handle dropped!
```

**✅ Solution:**
```rust
let material_handle = materials.add(StandardMaterial { .. });
commands.spawn((
    Mesh3d(mesh_handle),
    MeshMaterial3d(material_handle),
    // ...
));
```

## 8. System Ordering Issues

**❌ Problem:**
```rust
// UI updates before state changes
.add_systems(Update, (
    update_ui,
    process_input,  // Wrong order!
))
```

**✅ Solution:**
Order systems by dependencies:
```rust
.add_systems(Update, (
    // Input processing
    process_input,

    // State changes
    update_state,

    // UI updates (reads state)
    update_ui,
))
```

## 9. Not Filtering Queries Early

**❌ Problem:**
```rust
// Filter in loop (inefficient)
Query<(&A, Option<&B>, Option<&C>)>
// Then check in loop
```

**✅ Solution:**
```rust
// Filter in query (efficient)
Query<&A, (With<B>, Without<C>)>
```

## 10. BorderRadius as Separate Component

**❌ Problem:**
```rust
// BorderRadius is not a component
commands.spawn((
    Node { /* ... */ },
    BorderRadius::all(Val::Px(8.0)),  // Won't work
));
```

**✅ Solution:**
BorderRadius is a field on Node:
```rust
commands.spawn((
    Node {
        border_radius: BorderRadius::all(Val::Px(8.0)),
        ..default()
    },
    BackgroundColor(Color::WHITE),
));
```

## 11. LineHeight in TextFont

**❌ Problem:**
```rust
// LineHeight is not part of TextFont
TextFont {
    font_size: 16.0,
    line_height: LineHeight::Relative(1.2),  // Won't compile
    ..default()
}
```

**✅ Solution:**
LineHeight is a separate component:
```rust
commands.spawn((
    Text::new("Hello"),
    TextFont { font_size: 16.0, ..default() },
    LineHeight::Relative(1.2),  // Separate component
));
```

## 12. State Transitions Fire on Same State

**❌ Problem:**
```rust
// This fires OnExit/OnEnter even if already in that state
next_state.set(GameState::Playing);
```

**✅ Solution:**
Use `set_if_neq()` to only transition if state differs:
```rust
next_state.set_if_neq(GameState::Playing);
```

## 13. Query Methods Returning Results

**❌ Problem:**
```rust
// Some query methods now return Result
let components = entity_ref.get_components();  // May fail
```

**✅ Solution:**
Handle the Result properly:
```rust
if let Ok(components) = entity_ref.get_components() {
    // Process components
}
```

## 14. Using Entity::row() Instead of index()

**❌ Problem:**
```rust
// Old terminology
let row = entity.row();
```

**✅ Solution:**
Use current terminology:
```rust
let index = entity.index();
```

## 15. GlobalAmbientLight vs AmbientLight

**❌ Problem:**
```rust
// Mixing up ambient light types
app.insert_resource(AmbientLight { /* ... */ });  // Wrong for global
```

**✅ Solution:**
Use correct type for your use case:
```rust
// For scene-wide ambient light
app.insert_resource(GlobalAmbientLight {
    color: Color::WHITE,
    brightness: 0.2,
});

// For entity-specific ambient
commands.spawn(AmbientLight { /* ... */ });
```
