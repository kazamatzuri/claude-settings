# Bevy UI Development Reference

## Bevy UI Hierarchy

Bevy UI uses a flexbox-like layout system:

```rust
commands
    .spawn((
        Node {
            position_type: PositionType::Absolute,
            left: Val::Px(10.0),
            top: Val::Px(10.0),
            width: Val::Px(300.0),
            padding: UiRect::all(Val::Px(10.0)),
            flex_direction: FlexDirection::Column,
            border_radius: BorderRadius::all(Val::Px(8.0)),  // BorderRadius is a Node field
            ..default()
        },
        BackgroundColor(Color::srgba(0.1, 0.1, 0.1, 0.9)),
    ))
    .with_children(|parent| {
        parent.spawn((
            Text::new("Title"),
            TextFont { font_size: 16.0, ..default() },
            TextColor(Color::WHITE),
            LineHeight::Relative(1.2),  // LineHeight is a separate component
        ));
    });
```

## UI Component Pattern

**1. Marker Components for UI Elements**
```rust
#[derive(Component)]
pub struct SpellBar;

#[derive(Component)]
pub struct HoverTooltip;

#[derive(Component)]
pub struct InspectPanel;
```

**2. Setup System (Startup)**
```rust
pub fn setup_ui(mut commands: Commands) {
    commands.spawn((
        SpellBar,
        Node { /* layout */ },
        BackgroundColor(/* color */),
    ))
    .with_children(|parent| {
        // Child elements
    });
}
```

**3. Update System (Update)**
```rust
pub fn update_ui(
    state: Res<GameState>,
    mut query: Query<&mut Text, With<SpellBar>>,
) {
    for mut text in query.iter_mut() {
        **text = format!("State: {:?}", state);
    }
}
```

## UI Best Practices

### Layout Tips

- Use `Val::Px()` for fixed sizes
- Use `Val::Percent()` for responsive layouts
- Use `flex_direction: FlexDirection::Column` for vertical stacking
- Use `flex_direction: FlexDirection::Row` for horizontal stacking
- Use `justify_content` and `align_items` for alignment

### Positioning

**Absolute positioning (HUD elements):**
```rust
Node {
    position_type: PositionType::Absolute,
    left: Val::Px(10.0),
    top: Val::Px(10.0),
    ..default()
}
```

**Centered element:**
```rust
Node {
    position_type: PositionType::Absolute,
    left: Val::Percent(50.0),
    top: Val::Percent(50.0),
    margin: UiRect {
        left: Val::Px(-150.0),  // Half of width
        top: Val::Px(-100.0),   // Half of height
        ..default()
    },
    width: Val::Px(300.0),
    height: Val::Px(200.0),
    ..default()
}
```

### BorderRadius

BorderRadius is a field on the `Node` component:
```rust
Node {
    width: Val::Px(100.0),
    height: Val::Px(50.0),
    border_radius: BorderRadius::all(Val::Px(8.0)),
    ..default()
}

// Different radii per corner
Node {
    border_radius: BorderRadius {
        top_left: Val::Px(10.0),
        top_right: Val::Px(10.0),
        bottom_left: Val::Px(0.0),
        bottom_right: Val::Px(0.0),
    },
    ..default()
}
```

### Text and LineHeight

LineHeight is a separate component, not part of TextFont:
```rust
// Basic text
commands.spawn((
    Text::new("Hello World"),
    TextFont { font_size: 16.0, ..default() },
    TextColor(Color::WHITE),
));

// With custom line height
commands.spawn((
    Text::new("Multi-line\ntext here"),
    TextFont { font_size: 16.0, ..default() },
    TextColor(Color::WHITE),
    LineHeight::Relative(1.5),  // 1.5x font size
));

// Absolute line height
commands.spawn((
    Text::new("Fixed spacing"),
    TextFont { font_size: 16.0, ..default() },
    TextColor(Color::WHITE),
    LineHeight::Px(24.0),  // Fixed 24px line height
));
```

**Note:** Non-text areas of `Text` nodes are not pickable. Only the actual text content responds to pointer events.

### Visibility Control

```rust
// Show/hide with Display
mut node: Query<&mut Node, With<Panel>>

// Hide
node.display = Display::None;

// Show
node.display = Display::Flex;
```

### Color and Styling

```rust
// Background
BackgroundColor(Color::srgba(0.1, 0.1, 0.1, 0.9))

// Border
BorderColor::all(Color::srgba(0.3, 0.6, 0.9, 1.0))

// Highlight on selection
*bg_color = BackgroundColor(Color::srgba(0.2, 0.4, 0.6, 1.0));
*border_color = BorderColor::all(Color::srgba(0.3, 0.6, 0.9, 1.0));
```

### Text Updates

```rust
// Update text content
**text = "New content".to_string();

// Or with formatting
**text = format!("Value: {:.2}", value);

// Multi-line text
**text = "Line 1\nLine 2\nLine 3".to_string();
```

## Complete UI Example

```rust
pub fn setup_hud(mut commands: Commands) {
    // Container
    commands.spawn((
        Node {
            position_type: PositionType::Absolute,
            left: Val::Px(20.0),
            top: Val::Px(20.0),
            width: Val::Px(250.0),
            padding: UiRect::all(Val::Px(15.0)),
            flex_direction: FlexDirection::Column,
            row_gap: Val::Px(10.0),
            border_radius: BorderRadius::all(Val::Px(10.0)),
            ..default()
        },
        BackgroundColor(Color::srgba(0.1, 0.1, 0.15, 0.9)),
    ))
    .with_children(|parent| {
        // Title
        parent.spawn((
            Text::new("Player Stats"),
            TextFont { font_size: 18.0, ..default() },
            TextColor(Color::WHITE),
        ));

        // Health bar container
        parent.spawn((
            HealthBarContainer,
            Node {
                width: Val::Percent(100.0),
                height: Val::Px(20.0),
                border_radius: BorderRadius::all(Val::Px(4.0)),
                ..default()
            },
            BackgroundColor(Color::srgba(0.3, 0.1, 0.1, 1.0)),
        ))
        .with_children(|parent| {
            // Health bar fill
            parent.spawn((
                HealthBar,
                Node {
                    width: Val::Percent(100.0),
                    height: Val::Percent(100.0),
                    border_radius: BorderRadius::all(Val::Px(4.0)),
                    ..default()
                },
                BackgroundColor(Color::srgba(0.8, 0.2, 0.2, 1.0)),
            ));
        });

        // Stats text
        parent.spawn((
            StatsDisplay,
            Text::new("HP: 100/100"),
            TextFont { font_size: 14.0, ..default() },
            TextColor(Color::srgba(0.8, 0.8, 0.8, 1.0)),
            LineHeight::Relative(1.3),
        ));
    });
}
```
