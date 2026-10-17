/// Format a number of seconds into a readable string:
/// `format_seconds(200_000.0)` is `2 days, 7:33:20 hours`. After the days
/// the rest is always in hours: `1 day, 0:00:05 hours`.
pub fn format_seconds(seconds: f64) -> String {
    let minutes = (seconds / 60.0).floor();
    let seconds = seconds - 60.0 * minutes;
    let hours = (minutes / 60.0).floor();
    let minutes = minutes - 60.0 * hours;
    let days = (hours / 24.0).floor();
    let hours = hours - 24.0 * days;

    // After the days the rest is always in hours.
    let time = if hours > 0.0 || days > 0.0 {
        format!("{hours}:{minutes:02}:{:02} hours", seconds.floor())
    } else if minutes > 0.0 {
        format!("{minutes}:{:02} minutes", seconds.floor())
    } else {
        format!("{seconds:.2} seconds")
    };
    match days as u64 {
        0 => time,
        1 => format!("1 day, {time}"),
        days => format!("{days} days, {time}"),
    }
}

pub(crate) fn round2(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn format_seconds_matches_the_python_package() {
        assert_eq!(format_seconds(0.0), "0.00 seconds");
        assert_eq!(format_seconds(12.345), "12.35 seconds");
        assert_eq!(format_seconds(60.0), "1:00 minutes");
        assert_eq!(format_seconds(75.0), "1:15 minutes");
        assert_eq!(format_seconds(3_600.0), "1:00:00 hours");
        assert_eq!(format_seconds(3_725.0), "1:02:05 hours");
        assert_eq!(format_seconds(86_400.0), "1 day, 0:00:00 hours");
        assert_eq!(format_seconds(86_405.0), "1 day, 0:00:05 hours");
        assert_eq!(format_seconds(86_475.0), "1 day, 0:01:15 hours");
        assert_eq!(format_seconds(90_000.0), "1 day, 1:00:00 hours");
        assert_eq!(format_seconds(200_000.0), "2 days, 7:33:20 hours");
    }
}
