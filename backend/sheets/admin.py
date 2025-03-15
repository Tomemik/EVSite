from django.contrib import admin
from django.db import transaction
from .models import Manufacturer, Team, Tank, UpgradePath, TeamTank, Match, TeamMatch, default_upgrade_kits, \
    MatchResult, Substitute, TankLost, TeamResult, TeamLog, TankBox, TeamBox, ImportTank, ImportCriteria


class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance', 'score', 'total_money_earned', 'total_money_spent')
    search_fields = ('name',)

    def save_model(self, request, obj, form, change):
        if not change and not obj.upgrade_kits:
            obj.upgrade_kits = {tier: data.copy() for tier, data in default_upgrade_kits().items()}
        super().save_model(request, obj, form, change)

    def get_users(self, obj):
        return ", ".join([user.username for user in obj.members.all()])

    get_users.short_description = 'Users'


class BoxAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier', 'get_tanks', 'price', 'is_national')

    def get_tanks(self, obj):
        return ", ".join([tank.name for tank in obj.tanks.all()])
    get_tanks.short_description = 'Tanks'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if 'tanks' in form.cleaned_data:
            tanks = form.cleaned_data['tanks']
            obj.tanks.set(tanks)
            obj.save()


class TeamBoxAdmin(admin.ModelAdmin):
    list_display = ('team', 'box')

    def box(self, obj):
        return obj.box.name
    box.short_description = 'Box Name'


class TankAdmin(admin.ModelAdmin):
    list_display = ('name', 'battle_rating', 'price', 'rank', 'type')
    search_fields = ('name', 'type')
    list_filter = ('type', 'rank')


class UpgradePathAdmin(admin.ModelAdmin):
    list_display = ('from_tank', 'to_tank', 'required_kit_tier', 'cost')
    search_fields = ('from_tank__name', 'to_tank__name')
    list_filter = ('required_kit_tier',)


class TeamTankAdmin(admin.ModelAdmin):
    list_display = ('team', 'tank', 'is_upgradable', 'is_trad', 'is_ghost')
    search_fields = ('team__name', 'tank__name')
    list_filter = ('is_upgradable',)


class TeamMatchInline(admin.TabularInline):
    model = TeamMatch
    extra = 1
    filter_horizontal = ('tanks',)
    fields = ('team', 'side', 'tanks')
    show_change_link = True


class MatchAdmin(admin.ModelAdmin):
    list_display = ('datetime', 'mode', 'gamemode', 'best_of_number', 'map_selection')
    search_fields = ('mode', 'gamemode', 'map_selection')
    inlines = [TeamMatchInline]
    list_filter = ('mode', 'gamemode', 'datetime')


class TeamMatchAdmin(admin.ModelAdmin):
    list_display = ('match', 'team', 'side')
    search_fields = ('match__datetime', 'team__name')
    filter_horizontal = ('tanks',)
    list_filter = ('side',)


class TankLostInline(admin.TabularInline):
    model = TankLost
    extra = 1


class SubstituteInline(admin.TabularInline):
    model = Substitute
    extra = 1


class TeamResultInline(admin.TabularInline):
    model = TeamResult
    extra = 1


class MatchResultAdmin(admin.ModelAdmin):
    list_display = ('match', 'winning_side', 'judge')
    inlines = [TankLostInline, SubstituteInline, TeamResultInline]

    def judge(self, obj):
        return obj.judge.name if obj.judge else '-'


class TeamLogAdmin(admin.ModelAdmin):
    model = TeamLog


class ImportTankAdmin(admin.ModelAdmin):
    list_display = ('tank', 'discount', 'available_from', 'available_until', 'is_purchased', 'criteria')
    list_filter = ('is_purchased','available_from', 'available_until')


class ImportCriteriaAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_rank', 'max_rank', 'tank_type', 'is_active')
    list_filter = ('is_active', 'tank_type')
    actions = ['set_active']

    def set_active(self, request, queryset):
        """Deactivate other criteria and activate the selected one."""
        ImportCriteria.objects.update(is_active=False)  # Deactivate all
        queryset.update(is_active=True)  # Activate selected
        self.message_user(request, "Selected criteria set to active.")

    set_active.short_description = "Set selected criteria as active"



admin.site.register(MatchResult, MatchResultAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Tank, TankAdmin)
admin.site.register(UpgradePath, UpgradePathAdmin)
admin.site.register(TeamTank, TeamTankAdmin)
admin.site.register(Match, MatchAdmin)
admin.site.register(TeamMatch, TeamMatchAdmin)
admin.site.register(TeamLog, TeamLogAdmin)
admin.site.register(TankBox, BoxAdmin)
admin.site.register(TeamBox, TeamBoxAdmin)
admin.site.register(ImportTank, ImportTankAdmin)
admin.site.register(ImportCriteria, ImportCriteriaAdmin)

