"""ASCII buddy animation frames."""

SPRITE_FRAMES: dict[str, list[str]] = {
    "idle": [
        "[cyan] /\\_/\\\\\n( o.o )\n > ^ <\n[/cyan]",
        "[cyan] /\\_/\\\\\n( -.- )\n > ^ <\n[/cyan]",
        "[cyan] /\\_/\\\\\n( o.o )\n >>^<<\n[/cyan]",
    ],
    "thinking": [
        "[yellow] /\\_/\\\\\n( o.o )\n /|_|\\\\\n[/yellow]",
        "[yellow] /\\_/\\\\\n( o.O )\n /|_|\\\\\n[/yellow]",
        "[yellow] /\\_/\\\\\n( O.o )\n /|_|\\\\\n[/yellow]",
    ],
    "happy": [
        "[green] /\\_/\\\\\n( ^.^ )\n / > <\\\\\n[/green]",
        "[green] /\\_/\\\\\n( ^o^ )\n / > <\\\\\n[/green]",
        "[green] /\\_/\\\\\n( ^.^ )\n / >> \\\\\n[/green]",
    ],
    "error": [
        "[red] /\\_/\\\\\n( x.x )\n / ! !\\\\\n[/red]",
        "[red] /\\_/\\\\\n( X.X )\n / ! !\\\\\n[/red]",
        "[red] /\\_/\\\\\n( x.x )\n / !!!\\\\\n[/red]",
    ],
    "sleep": [
        "[blue] /\\_/\\\\\n( -.- )\n z Z z\n[/blue]",
        "[blue] /\\_/\\\\\n( -.- )\n Z z Z\n[/blue]",
        "[blue] /\\_/\\\\\n( -.- )\n z z Z\n[/blue]",
    ],
}
