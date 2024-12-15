while true
do
    current_day=$(date -u +%u)
    current_hour=$(date -u +%H)

    if [ "$current_day" -eq 2 ] && [ "$current_hour" -eq 0 ]; then
        echo "Running special offers job..."
        python manage.py create_special_offers
        sleep 3600
    fi

    sleep 60
done