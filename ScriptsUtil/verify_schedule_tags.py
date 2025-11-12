#!/usr/bin/env python3
"""
Verify Schedule tags extraction from EC2 instances.
Tests that the case-sensitive 'Schedule' tag is properly extracted.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.aws_service import AWSService

def verify_schedule_tags():
    """Verify that Schedule tags are properly extracted from instances."""
    print("=" * 80)
    print("Verificando extracción de tags 'Schedule' de instancias EC2")
    print("=" * 80)
    print()

    # Initialize AWS service
    aws_service = AWSService()

    print("🔄 Obteniendo datos de instancias...")
    instances_data = aws_service.get_aws_data()

    if not instances_data:
        print("❌ No se pudieron obtener datos de instancias")
        return

    print(f"✅ {len(instances_data)} instancias encontradas\n")

    # Find instances with Schedule tag
    instances_with_schedule = []
    instances_without_schedule = []

    for instance in instances_data:
        name = instance.get('Name', 'Unknown')
        instance_id = instance.get('ID', 'Unknown')
        schedule = instance.get('Schedule', None)

        if schedule:
            instances_with_schedule.append((name, instance_id, schedule))
        else:
            instances_without_schedule.append((name, instance_id))

    # Display results
    print("📊 INSTANCIAS CON TAG 'Schedule':")
    print("-" * 80)
    if instances_with_schedule:
        for name, instance_id, schedule in instances_with_schedule:
            print(f"✅ {name}")
            print(f"   Instance ID: {instance_id}")
            print(f"   Schedule: {schedule}")
            print()
    else:
        print("⚠️  Ninguna instancia tiene el tag 'Schedule'")
        print()

    print("=" * 80)
    print("📊 INSTANCIAS SIN TAG 'Schedule':")
    print("-" * 80)
    if instances_without_schedule:
        print(f"Total: {len(instances_without_schedule)} instancias\n")
        for name, instance_id in instances_without_schedule[:10]:  # Show first 10
            print(f"   • {name} ({instance_id})")
        if len(instances_without_schedule) > 10:
            print(f"   ... y {len(instances_without_schedule) - 10} más")
    else:
        print("✅ Todas las instancias tienen tag 'Schedule'")

    print()
    print("=" * 80)
    print("💡 RESUMEN:")
    print(f"   Total instancias: {len(instances_data)}")
    print(f"   Con Schedule tag: {len(instances_with_schedule)}")
    print(f"   Sin Schedule tag: {len(instances_without_schedule)}")
    print()
    print("📝 NOTA:")
    print("   Para agregar el tag 'Schedule' a una instancia:")
    print("   1. Ir a AWS EC2 Console")
    print("   2. Seleccionar la instancia")
    print("   3. Tags → Manage tags → Add tag")
    print("   4. Key: Schedule (case sensitive, con mayúscula)")
    print("   5. Value: Weekends | Nights | BusinessHours")
    print("=" * 80)

if __name__ == "__main__":
    try:
        verify_schedule_tags()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
